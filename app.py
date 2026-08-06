from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import streamlit as st

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Güneş Doğalgaz - Servis Yönetim Sistemi",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- TÜRKÇE AY VE TARİH SÖZLÜĞÜ ---
TURKCE_AYLAR = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


def turkce_tarih_formatla(tarih_obj):
  if not tarih_obj:
    return ""
  if isinstance(tarih_obj, str):
    try:
      tarih_obj = datetime.strptime(tarih_obj, "%Y-%m-%d").date()
    except:
      return tarih_obj
  gun = tarih_obj.day
  ay = TURKCE_AYLAR.get(tarih_obj.month, "")
  yil = tarih_obj.year
  return f"{gun} {ay} {yil}"


# --- VERİTABANI BAĞLANTISI VE TABLOLAR ---
def get_db():
  conn = sqlite3.connect("gunes_dogalgaz.db", check_same_thread=False)
  return conn


def init_db():
  conn = get_db()
  c = conn.cursor()

  # 1. Kayıtlar Tablosu
  c.execute("""CREATE TABLE IF NOT EXISTS kayitlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seri_no TEXT,
                    musteri_adi TEXT,
                    telefon TEXT,
                    adres TEXT,
                    proje_tarihi TEXT,
                    proje_ayi TEXT,
                    usta_adi TEXT,
                    kolon_sayisi INTEGER DEFAULT 0,
                    ic_tesisat_sayisi INTEGER DEFAULT 0,
                    diger_islemler TEXT,
                    armadas_surec_adimi TEXT,
                    toplam_bedel REAL DEFAULT 0.0,
                    alinan_tutar REAL DEFAULT 0.0,
                    kalan_tutar REAL DEFAULT 0.0,
                    odeme_yontemi TEXT,
                    sayac_seri_no TEXT,
                    notlar TEXT DEFAULT '',
                    durum TEXT
                )""")

  # 2. Ustalar Tablosu
  c.execute("""CREATE TABLE IF NOT EXISTS ustalar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_soyad TEXT UNIQUE,
                    uzmanlik TEXT,
                    telefon TEXT,
                    durum TEXT DEFAULT 'Aktif'
                )""")

  # 3. Kullanıcılar Tablosu
  c.execute("""CREATE TABLE IF NOT EXISTS kullanicilar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_adi TEXT UNIQUE,
                    sifre TEXT,
                    ad_soyad TEXT,
                    telefon TEXT,
                    rol TEXT,
                    durum TEXT,
                    izin_kayit_ekle INTEGER DEFAULT 1,
                    izin_kayit_duzenle INTEGER DEFAULT 1,
                    izin_kayit_sil INTEGER DEFAULT 0,
                    izin_usta_yonetim INTEGER DEFAULT 1,
                    izin_rapor_goruntule INTEGER DEFAULT 1,
                    izin_kullanici_yonetim INTEGER DEFAULT 0
                )""")

  # --- MİGRASYON / EKSİK SÜTUN KONTROLLERİ ---
  c.execute("PRAGMA table_info(kayitlar)")
  kayitlar_sutunlar = [col[1] for col in c.fetchall()]
  if "diger_islemler" not in kayitlar_sutunlar:
    c.execute("ALTER TABLE kayitlar ADD COLUMN diger_islemler TEXT DEFAULT ''")
  if "proje_ayi" not in kayitlar_sutunlar:
    c.execute("ALTER TABLE kayitlar ADD COLUMN proje_ayi TEXT DEFAULT ''")
  if "notlar" not in kayitlar_sutunlar:
    c.execute("ALTER TABLE kayitlar ADD COLUMN notlar TEXT DEFAULT ''")
  if "kolon_sayisi" not in kayitlar_sutunlar:
    c.execute("ALTER TABLE kayitlar ADD COLUMN kolon_sayisi INTEGER DEFAULT 0")
  if "ic_tesisat_sayisi" not in kayitlar_sutunlar:
    c.execute(
        "ALTER TABLE kayitlar ADD COLUMN ic_tesisat_sayisi INTEGER DEFAULT 0"
    )

  # Admin Hesabı Kontrolü
  c.execute("SELECT COUNT(*) FROM kullanicilar WHERE kullanici_adi = 'admin'")
  if c.fetchone()[0] == 0:
    c.execute("""
            INSERT INTO kullanicilar (
                kullanici_adi, sifre, ad_soyad, telefon, rol, durum,
                izin_kayit_ekle, izin_kayit_duzenle, izin_kayit_sil,
                izin_usta_yonetim, izin_rapor_goruntule, izin_kullanici_yonetim
            ) VALUES ('admin', '1234', 'Yönetici Anıl', '05000000000', 'Yönetici', 'Aktif', 1, 1, 1, 1, 1, 1)
        """)

  # Varsayılan Ustalar Ekleme
  c.execute("SELECT COUNT(*) FROM ustalar")
  if c.fetchone()[0] == 0:
    varsayilan_ustalar = [
        ("MEHMET BEKİROĞLU", "Doğalgaz Tesisatı", "0532 111 2233", "Aktif"),
        ("VATAN SİNAN", "Kombi & Tesisat", "0533 222 3344", "Aktif"),
        ("SURİYELİ MUHAMMET", "İç Tesisat", "0534 333 4455", "Aktif"),
    ]
    for usta in varsayilan_ustalar:
      try:
        c.execute(
            "INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum) VALUES"
            " (?, ?, ?, ?)",
            usta,
        )
      except sqlite3.IntegrityError:
        pass

  conn.commit()
  conn.close()


init_db()

# --- OTURUM (SESSION) YÖNETİMİ ---
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
  st.session_state["user_info"] = None
if "current_page" not in st.session_state:
  st.session_state["current_page"] = "Dashboard"
if "theme_mode" not in st.session_state:
  st.session_state["theme_mode"] = "Karanlık Mod"

conn = get_db()

# ==========================================
# GİRİŞ / KAYIT EKRANI
# ==========================================
if not st.session_state["logged_in"]:
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='text-align: center;'>
            <h1 style='color: #f59e0b;'>🔥 Güneş Doğalgaz</h1>
            <h3>Servis & Proje Yönetim Sistemi</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_giris, tab_kayit = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])

    with tab_giris:
      with st.form("login_form"):
        kullanici_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        btn_login = st.form_submit_button("Giriş Yap", use_container_width=True)

        if btn_login:
          cursor = conn.cursor()
          cursor.execute(
              """
                        SELECT id, kullanici_adi, sifre, ad_soyad, telefon, rol, durum,
                               izin_kayit_ekle, izin_kayit_duzenle, izin_kayit_sil, 
                               izin_usta_yonetim, izin_rapor_goruntule, izin_kullanici_yonetim 
                        FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?
                    """,
              (kullanici_adi.strip(), sifre.strip()),
          )
          user = cursor.fetchone()
          if user:
            if user[6] != "Aktif":
              st.error(
                  "⚠️ Hesabınız henüz onaylanmamıştır veya pasife alınmıştır."
              )
            else:
              st.session_state["logged_in"] = True
              st.session_state["user_info"] = {
                  "id": user[0],
                  "kullanici_adi": user[1],
                  "ad_soyad": user[3],
                  "telefon": user[4],
                  "rol": user[5],
                  "durum": user[6],
                  "izin_kayit_ekle": bool(user[7]),
                  "izin_kayit_duzenle": bool(user[8]),
                  "izin_kayit_sil": bool(user[9]),
                  "izin_usta_yonetim": bool(user[10]),
                  "izin_rapor_goruntule": bool(user[11]),
                  "izin_kullanici_yonetim": bool(user[12]),
              }
              st.rerun()
          else:
            st.error("Kullanıcı adı veya şifre hatalı!")

    with tab_kayit:
      with st.form("register_form"):
        new_ad_soyad = st.text_input("Ad Soyad*")
        new_username = st.text_input("Kullanıcı Adı*")
        new_tel = st.text_input("Cep Telefonu No*")
        new_password = st.text_input("Şifre*", type="password")
        btn_register = st.form_submit_button(
            "Kayıt Başvurusu Yap", use_container_width=True
        )

        if btn_register and new_username and new_password:
          try:
            cursor = conn.cursor()
            cursor.execute(
                """
                            INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, telefon, rol, durum)
                            VALUES (?, ?, ?, ?, 'Personel', 'Onay Bekliyor')
                        """,
                (
                    new_username.strip(),
                    new_password.strip(),
                    new_ad_soyad.strip(),
                    new_tel.strip(),
                ),
            )
            conn.commit()
            st.success(
                "✅ Kayıt başvurunuz alındı! Yöneticinizin onaylamasını"
                " bekleyiniz."
            )
          except sqlite3.IntegrityError:
            st.error("Bu kullanıcı adı zaten alınmış.")

  st.stop()

# --- İZİN KONTROLLERİ ---
user_info = st.session_state.get("user_info", {}) or {}
izin_kayit_ekle = user_info.get("izin_kayit_ekle", True)
izin_kayit_duzenle = user_info.get("izin_kayit_duzenle", True)
izin_kayit_sil = user_info.get("izin_kayit_sil", False)
izin_usta_yonetim = user_info.get("izin_usta_yonetim", True)
izin_rapor_goruntule = user_info.get("izin_rapor_goruntule", True)
izin_kullanici_yonetim = user_info.get("izin_kullanici_yonetim", False)
is_admin = user_info.get("rol") == "Yönetici" or izin_kullanici_yonetim

# ==========================================
# SOL MENÜ (SİDEBAR) VE TEMA DEĞİŞTİRİCİ
# ==========================================
with st.sidebar:
  st.markdown(
      """
    <div class="brand-container">
        <div class="brand-icon">🔥</div>
        <div>
            <div class="brand-title">Güneş Doğalgaz</div>
            <div class="brand-subtitle">Servis Yönetim Sistemi</div>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # Tema Seçimi
  st.session_state["theme_mode"] = st.radio(
      "🎨 Tema Modu",
      ["Karanlık Mod", "Aydınlık Mod"],
      index=0
      if st.session_state["theme_mode"] == "Karanlık Mod"
      else 1,
      horizontal=True,
  )
  st.markdown("---")

  if st.button("🗂️  Dashboard", use_container_width=True):
    st.session_state["current_page"] = "Dashboard"
    st.rerun()
  if st.button("📋  Kayıtlar", use_container_width=True):
    st.session_state["current_page"] = "Kayıtlar"
    st.rerun()
  if st.button("✏️  Düzenleme", use_container_width=True):
    st.session_state["current_page"] = "Düzenleme"
    st.rerun()
  if st.button("👷  Ustalar", use_container_width=True):
    st.session_state["current_page"] = "Ustalar"
    st.rerun()
  if st.button("📊  Raporlar & Analiz", use_container_width=True):
    st.session_state["current_page"] = "Raporlar & Analiz"
    st.rerun()
  if st.button("⚙️  Kullanıcılar & İzinler", use_container_width=True):
    st.session_state["current_page"] = "Kullanıcı Onayları & İzinler"
    st.rerun()

  u_ad = user_info.get("ad_soyad", "Kullanıcı")
  u_rol = user_info.get("rol", "Personel")

  st.markdown(
      f"""
    <div class="sidebar-user-box">
        <div class="user-avatar">{u_ad[:2].upper() if u_ad else 'US'}</div>
        <div>
            <div style="font-size:13px; font-weight:600;">{u_ad}</div>
            <div style="font-size:11px; color:#f59e0b;">{u_rol}</div>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  st.markdown("<br>", unsafe_allow_html=True)
  if st.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.rerun()

sayfa = st.session_state["current_page"]
is_dark = st.session_state["theme_mode"] == "Karanlık Mod"

# --- DİNAMİK CSS / TASARIM (TEMA UYUMLU) ---
if is_dark:
  css_style = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #0b101d; color: #f3f4f6; }
        [data-testid="stSidebar"] { background-color: #0d1424; border-right: 1px solid #1a233a; padding-top: 10px; }
        [data-testid="stSidebar"] .stButton button {
            width: 100%; background-color: #131c2e; color: #e2e8f0; border: 1px solid #1e2a45;
            border-radius: 12px; padding: 12px 18px; text-align: left; font-weight: 500; font-size: 14px;
            margin-bottom: 6px; transition: all 0.2s ease-in-out;
        }
        [data-testid="stSidebar"] .stButton button:hover { background-color: #1f293d; color: #ffffff; border-color: #f59e0b; }
        .brand-container { display: flex; align-items: center; gap: 12px; margin-bottom: 15px; padding: 0 10px; }
        .brand-icon { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
        .brand-title { font-weight: 700; font-size: 16px; color: #ffffff; }
        .brand-subtitle { font-size: 11px; color: #64748b; }
        .dashboard-card { background-color: #131c2e; border: 1px solid #1e2a45; border-radius: 14px; padding: 20px; }
        .card-value { font-size: 24px; font-weight: 700; color: #ffffff; }
        .card-label { font-size: 12px; color: #94a3b8; }
        .sidebar-user-box { margin-top: 10px; padding: 12px; background-color: #131c2e; border-radius: 12px; display: flex; align-items: center; gap: 12px; border: 1px solid #1e2a45; color: #fff; }
        .user-avatar { width: 38px; height: 38px; border-radius: 50%; background-color: #1e293b; color: #f59e0b; font-weight: 700; display: flex; align-items: center; justify-content: center; border: 1px solid #f59e0b; }
    </style>
    """
else:
  css_style = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #f8fafc; color: #1e293b; }
        [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; padding-top: 10px; }
        [data-testid="stSidebar"] .stButton button {
            width: 100%; background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;
            border-radius: 12px; padding: 12px 18px; text-align: left; font-weight: 500; font-size: 14px;
            margin-bottom: 6px; transition: all 0.2s ease-in-out;
        }
        [data-testid="stSidebar"] .stButton button:hover { background-color: #e2e8f0; color: #0f172a; border-color: #f59e0b; }
        .brand-container { display: flex; align-items: center; gap: 12px; margin-bottom: 15px; padding: 0 10px; }
        .brand-icon { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
        .brand-title { font-weight: 700; font-size: 16px; color: #0f172a; }
        .brand-subtitle { font-size: 11px; color: #64748b; }
        .dashboard-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card-value { font-size: 24px; font-weight: 700; color: #0f172a; }
        .card-label { font-size: 12px; color: #64748b; }
        .sidebar-user-box { margin-top: 10px; padding: 12px; background-color: #f1f5f9; border-radius: 12px; display: flex; align-items: center; gap: 12px; border: 1px solid #cbd5e1; color: #0f172a; }
        .user-avatar { width: 38px; height: 38px; border-radius: 50%; background-color: #e2e8f0; color: #d97706; font-weight: 700; display: flex; align-items: center; justify-content: center; border: 1px solid #d97706; }
    </style>
    """

st.markdown(css_style, unsafe_allow_html=True)


# ==========================================
# YARDIMCI FONKSİYON: TABLO FORMATLAMA
# ==========================================
def format_table_df(df_input):
  if df_input.empty:
    return pd.DataFrame(columns=[
        "Seç",
        "Kayıt Tarihi",
        "Ay",
        "Müşteri Adı",
        "Sorumlu Usta",
        "Kolon Sayısı",
        "İç Tesisat",
        "Armadaş Durumu",
        "Diğer İşlemler",
        "Toplam Bedel (TL)",
        "Alınan Ödeme (TL)",
        "Kalan Alacak (TL)",
        "Ödeme Tipi",
        "Sayaç Seri No",
        "Notlar",
        "id",
    ])

  df = df_input.copy()
  if "Seç" not in df.columns:
    df["Seç"] = False

  df_renamed = df.rename(columns={
      "proje_tarihi": "Kayıt Tarihi",
      "proje_ayi": "Ay",
      "musteri_adi": "Müşteri Adı",
      "usta_adi": "Sorumlu Usta",
      "kolon_sayisi": "Kolon Sayısı",
      "ic_tesisat_sayisi": "İç Tesisat",
      "armadas_surec_adimi": "Armadaş Durumu",
      "diger_islemler": "Diğer İşlemler",
      "toplam_bedel": "Toplam Bedel (TL)",
      "alinan_tutar": "Alınan Ödeme (TL)",
      "kalan_tutar": "Kalan Alacak (TL)",
      "odeme_yontemi": "Ödeme Tipi",
      "sayac_seri_no": "Sayaç Seri No",
      "notlar": "Notlar",
  })

  sutun_sirasi = [
      "Seç",
      "Kayıt Tarihi",
      "Ay",
      "Müşteri Adı",
      "Sorumlu Usta",
      "Kolon Sayısı",
      "İç Tesisat",
      "Armadaş Durumu",
      "Diğer İşlemler",
      "Toplam Bedel (TL)",
      "Alınan Ödeme (TL)",
      "Kalan Alacak (TL)",
      "Ödeme Tipi",
      "Sayaç Seri No",
      "Notlar",
      "id",
  ]

  mevcut_sutunlar = [c for c in sutun_sirasi if c in df_renamed.columns]
  return df_renamed[mevcut_sutunlar]


# ==========================================
# SAYFA 1: DASHBOARD
# ==========================================
if sayfa == "Dashboard":
  col_head1, col_head2 = st.columns([3, 1])
  with col_head1:
    st.title("Merkezi İş Takip Ekranı")
    st.caption(f"Hoş geldiniz, **{user_info.get('ad_soyad', '')}**")
  with col_head2:
    if izin_kayit_ekle:
      yeni_kayit_modal = st.button("➕ Yeni Proje Kaydı", use_container_width=True)
    else:
      yeni_kayit_modal = False

  df_kayitlar = pd.read_sql_query(
      "SELECT * FROM kayitlar ORDER BY id DESC", conn
  )

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    st.markdown(
        f'<div class="dashboard-card"><div'
        f' class="card-value">{len(df_kayitlar)}</div><div'
        ' class="card-label">Toplam Proje</div></div>',
        unsafe_allow_html=True,
    )
  with c2:
    st.markdown(
        f'<div class="dashboard-card"><div'
        f' class="card-value">₺{df_kayitlar["alinan_tutar"].sum() if not df_kayitlar.empty else 0:,.0f}</div><div'
        ' class="card-label">Toplanan Alacak</div></div>',
        unsafe_allow_html=True,
    )
  with c3:
    st.markdown(
        f'<div class="dashboard-card"><div'
        f' class="card-value">₺{df_kayitlar["kalan_tutar"].sum() if not df_kayitlar.empty else 0:,.0f}</div><div'
        ' class="card-label">Bekleyen Ödeme</div></div>',
        unsafe_allow_html=True,
    )
  with c4:
    st.markdown(
        f'<div class="dashboard-card"><div'
        f' class="card-value">{len(df_kayitlar[df_kayitlar["kalan_tutar"] > 0]) if not df_kayitlar.empty else 0}</div><div'
        ' class="card-label">Borçlu Müşteri</div></div>',
        unsafe_allow_html=True,
    )

  st.markdown("<br>", unsafe_allow_html=True)

  if (
      yeni_kayit_modal or st.session_state.get("form_acik", False)
  ) and izin_kayit_ekle:
    st.session_state["form_acik"] = True
    with st.expander("📝 Yeni Proje Kaydı Ekle", expanded=True):
      df_ustalar_list = pd.read_sql_query(
          "SELECT ad_soyad FROM ustalar WHERE durum='Aktif'", conn
      )
      u_options = (
          df_ustalar_list["ad_soyad"].tolist()
          if not df_ustalar_list.empty
          else ["Usta Eklenmemiş"]
      )

      with st.form("yeni_kayit_formu", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
          proje_tarihi_input = st.date_input("Kayıt Tarihi", datetime.now())
          musteri_adi = st.text_input("Müşteri Adı*")
          telefon = st.text_input("Telefon")
          adres = st.text_area("Adres", height=68)
          usta_adi = st.selectbox("Sorumlu Usta", u_options)

        with col_f2:
          kolon_sayisi_in = st.number_input(
              "Kolon Sayısı", min_value=0, step=1, value=0
          )
          ic_tesisat_sayisi_in = st.number_input(
              "İç Tesisat Sayısı", min_value=0, step=1, value=0
          )
          toplam_bedel = st.number_input(
              "Toplam Bedel (TL)*", min_value=0.0, step=500.0
          )
          alinan_tutar = st.number_input(
              "Alınan Ödeme (TL)", min_value=0.0, step=500.0
          )
          kalan_tutar_hesaplanan = max(0.0, toplam_bedel - alinan_tutar)
          st.info(f"**Hesaplanan Kalan:** ₺{kalan_tutar_hesaplanan:,.2f}")

        with col_f3:
          odeme_yontemi = st.selectbox(
              "Ödeme Tipi",
              ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"],
          )
          armadas_surec_adimi = st.selectbox(
              "Armadaş Durumu",
              [
                  "Armadaş Dijital Onay Bekliyor",
                  "Onay Bekliyor",
                  "Armadaş Eksik / Red Aldı",
                  "Gaz Açıldı / Müşteriye Teslim Edildi",
                  "Randevu Alındı",
              ],
          )
          diger_islemler = st.multiselect(
              "Diğer İşlemler",
              [
                  "Cihaz Değişimi",
                  "Randevu Reddi",
                  "Kolon Tesisatı",
                  "İç Tesisat",
              ],
          )
          sayac_seri_no = st.text_input("Sayaç Seri No")
          notlar = st.text_input("Notlar")

        if st.form_submit_button("💾 Kaydet") and musteri_adi.strip():
          seri_no = f"GZ-{datetime.now().year}-{len(df_kayitlar) + 1:03d}"
          durum = (
              "Tamamlandı" if kalan_tutar_hesaplanan == 0 else "Devam Ediyor"
          )
          formatli_tarih = turkce_tarih_formatla(proje_tarihi_input)
          proje_ayi = f"{proje_tarihi_input.year}-{proje_tarihi_input.month:02d}"
          diger_islemler_str = (
              ", ".join(diger_islemler) if diger_islemler else "Yok"
          )

          cursor = conn.cursor()
          cursor.execute(
              """
                        INSERT INTO kayitlar (seri_no, musteri_adi, telefon, adres, proje_tarihi, proje_ayi, usta_adi, 
                        kolon_sayisi, ic_tesisat_sayisi, armadas_surec_adimi, diger_islemler, toplam_bedel, alinan_tutar, kalan_tutar, odeme_yontemi, sayac_seri_no, notlar, durum)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
              (
                  seri_no,
                  musteri_adi.strip(),
                  telefon,
                  adres,
                  formatli_tarih,
                  proje_ayi,
                  usta_adi,
                  kolon_sayisi_in,
                  ic_tesisat_sayisi_in,
                  armadas_surec_adimi,
                  diger_islemler_str,
                  toplam_bedel,
                  alinan_tutar,
                  kalan_tutar_hesaplanan,
                  odeme_yontemi,
                  sayac_seri_no,
                  notlar,
                  durum,
              ),
          )
          conn.commit()
          st.success("Kayıt Başarılı!")
          st.session_state["form_acik"] = False
          st.rerun()

  st.subheader("Son Projeler")
  if not df_kayitlar.empty:
    formatted_df = format_table_df(df_kayitlar)
    st.dataframe(
        formatted_df.drop(columns=["Seç"], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
  st.title("📋 Tüm Kayıtlar ve Kaldırma Paneli")
  st.caption(
      "☑️ Tablodan silmek/kaldırmak istediğiniz kayıtların **Seç** kutucuğunu"
      " işaretleyip aşağıdaki butona basabilirsiniz."
  )

  df_kayitlar = pd.read_sql_query(
      "SELECT * FROM kayitlar ORDER BY id DESC", conn
  )
  if not df_kayitlar.empty:
    formatted_df = format_table_df(df_kayitlar)

    edited_kayitlar_df = st.data_editor(
        formatted_df,
        column_config={
            "Seç": st.column_config.CheckboxColumn("Seç", default=False),
            "Toplam Bedel (TL)": st.column_config.NumberColumn(
                format="%.2f", disabled=True
            ),
            "Alınan Ödeme (TL)": st.column_config.NumberColumn(
                format="%.2f", disabled=True
            ),
            "Kalan Alacak (TL)": st.column_config.NumberColumn(
                format="%.2f", disabled=True
            ),
        },
        use_container_width=True,
        hide_index=True,
        key="kayitlar_tablo_editor",
    )

    if st.button("🗑️ Seçili Kayıtları Sistemden Kaldır / Sil", type="primary"):
      secilenler = edited_kayitlar_df[edited_kayitlar_df["Seç"] == True]
      if not secilenler.empty:
        cursor = conn.cursor()
        for _, row in secilenler.iterrows():
          cursor.execute("DELETE FROM kayitlar WHERE id = ?", (row["id"],))
        conn.commit()
        st.warning(
            f"⚠️ Seçilen {len(secilenler)} kayıt başarıyla kaldırıldı/silindi!"
        )
        st.rerun()
      else:
        st.info(
            "Lütfen kaldırmak için tablodan en az bir satırın 'Seç' kutucuğunu"
            " işaretleyin."
        )
  else:
    st.info("Sistemde kayıtlı proje bulunmamaktadır.")

# ==========================================
# SAYFA 3: DÜZENLEME
# ==========================================
elif sayfa == "Düzenleme":
  st.title("✏️ Proje & Kayıt Düzenleme Paneli")
  df_kayitlar = pd.read_sql_query(
      "SELECT * FROM kayitlar ORDER BY id DESC", conn
  )

  if df_kayitlar.empty:
    st.info("Düzenlenecek kayıt bulunamadı.")
  else:
    kayit_secenekleri = {
        f"#{row['id']} - {row['musteri_adi']} (Tarih: {row['proje_tarihi']} | Tel:"
        f" {row['telefon']})": row["id"]
        for _, row in df_kayitlar.iterrows()
    }

    selected_label = st.selectbox(
        "🔍 Düzenlemek İstediğiniz Kaydı Seçin:", list(kayit_secenekleri.keys())
    )
    selected_id = kayit_secenekleri[selected_label]
    row_data = df_kayitlar[df_kayitlar["id"] == selected_id].iloc[0]

    st.markdown("---")
    st.subheader(f"🛠️ Müşteri: {row_data['musteri_adi']}")

    if not izin_kayit_duzenle:
      st.warning("⚠️ Kayıt düzenleme yetkiniz bulunmamaktadır.")
    else:
      df_ustalar_list = pd.read_sql_query(
          "SELECT ad_soyad FROM ustalar WHERE durum='Aktif'", conn
      )
      u_options = (
          df_ustalar_list["ad_soyad"].tolist()
          if not df_ustalar_list.empty
          else [row_data["usta_adi"]]
      )
      if row_data["usta_adi"] not in u_options:
        u_options.append(row_data["usta_adi"])

      with st.form("duzenleme_formu"):
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
          e_musteri = st.text_input(
              "Müşteri Adı", value=str(row_data["musteri_adi"])
          )
          e_tarih = st.text_input(
              "Kayıt Tarihi", value=str(row_data["proje_tarihi"])
          )
          e_tel = st.text_input("Telefon", value=str(row_data["telefon"] or ""))
          e_adres = st.text_area(
              "Adres", value=str(row_data["adres"] or ""), height=68
          )

        with col_e2:
          e_kolon = st.number_input(
              "Kolon Sayısı",
              value=int(row_data.get("kolon_sayisi", 0) or 0),
              min_value=0,
              step=1,
          )
          e_ic = st.number_input(
              "İç Tesisat Sayısı",
              value=int(row_data.get("ic_tesisat_sayisi", 0) or 0),
              min_value=0,
              step=1,
          )
          e_toplam = st.number_input(
              "Toplam Bedel (TL)",
              value=float(row_data["toplam_bedel"]),
              step=500.0,
          )
          e_alinan = st.number_input(
              "Alınan Ödeme (TL)",
              value=float(row_data["alinan_tutar"]),
              step=500.0,
          )
          e_kalan = max(0.0, e_toplam - e_alinan)
          st.info(f"**Güncellenecek Kalan:** ₺{e_kalan:,.2f}")

        with col_e3:
          odeme_index = (
              ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"].index(
                  row_data["odeme_yontemi"]
              )
              if row_data["odeme_yontemi"]
              in ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"]
              else 0
          )
          e_odeme_tipi = st.selectbox(
              "Ödeme Tipi",
              ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"],
              index=odeme_index,
          )
          e_usta = st.selectbox(
              "Sorumlu Usta",
              u_options,
              index=u_options.index(row_data["usta_adi"])
              if row_data["usta_adi"] in u_options
              else 0,
          )
          armadas_opts = [
              "Armadaş Dijital Onay Bekliyor",
              "Onay Bekliyor",
              "Armadaş Eksik / Red Aldı",
              "Gaz Açıldı / Müşteriye Teslim Edildi",
              "Randevu Alındı",
          ]
          arm_index = (
              armadas_opts.index(row_data["armadas_surec_adimi"])
              if row_data["armadas_surec_adimi"] in armadas_opts
              else 0
          )
          e_armadas = st.selectbox(
              "Armadaş Durumu", armadas_opts, index=arm_index
          )
          e_diger = st.text_input(
              "Diğer İşlemler", value=str(row_data["diger_islemler"] or "")
          )
          e_sayac = st.text_input(
              "Sayaç Seri No", value=str(row_data["sayac_seri_no"] or "")
          )
          e_notlar = st.text_input(
              "Notlar", value=str(row_data["notlar"] or "")
          )

        btn_col1, btn_col2 = st.columns([2, 1])
        with btn_col1:
          if st.form_submit_button(
              "💾 Değişiklikleri Kaydet", use_container_width=True
          ):
            cursor = conn.cursor()
            cursor.execute(
                """
                            UPDATE kayitlar SET 
                                musteri_adi=?, proje_tarihi=?, telefon=?, adres=?,
                                kolon_sayisi=?, ic_tesisat_sayisi=?, toplam_bedel=?, alinan_tutar=?, kalan_tutar=?, odeme_yontemi=?,
                                usta_adi=?, armadas_surec_adimi=?, diger_islemler=?, sayac_seri_no=?, notlar=?
                            WHERE id=?
                        """,
                (
                    e_musteri,
                    e_tarih,
                    e_tel,
                    e_adres,
                    e_kolon,
                    e_ic,
                    e_toplam,
                    e_alinan,
                    e_kalan,
                    e_odeme_tipi,
                    e_usta,
                    e_armadas,
                    e_diger,
                    e_sayac,
                    e_notlar,
                    selected_id,
                ),
            )
            conn.commit()
            st.success("✅ Kayıt başarıyla güncellendi!")
            st.rerun()
        with btn_col2:
          if izin_kayit_sil and st.form_submit_button(
              "🗑️ Kaydı Sil", use_container_width=True
          ):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kayitlar WHERE id=?", (selected_id,))
            conn.commit()
            st.warning("⚠️ Kayıt silindi!")
            st.rerun()

# ==========================================
# SAYFA 4: USTALAR
# ==========================================
elif sayfa == "Ustalar":
  st.title("🔧 Usta Yönetim Paneli")

  if not izin_usta_yonetim:
    st.warning("⚠️ Usta yönetimi için yetkiniz bulunmamaktadır.")
  else:
    tab_u1, tab_u2 = st.tabs(
        ["📋 Aktif Ustalar ve İşler", "➕ Yeni Usta Ekle / Sil"]
    )

    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar", conn)
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)

    with tab_u1:
      if not df_ustalar.empty:
        for idx, usta in df_ustalar.iterrows():
          u_isleri = (
              df_kayitlar[df_kayitlar["usta_adi"] == usta["ad_soyad"]]
              if not df_kayitlar.empty
              else pd.DataFrame()
          )
          status_color = "🟢" if usta["durum"] == "Aktif" else "🔴"
          with st.expander(
              f"{status_color} {usta['ad_soyad']} - Uzmanlık:"
              f" {usta['uzmanlik']} | Tel: {usta['telefon']} | Toplam Proje:"
              f" {len(u_isleri)}"
          ):
            if not u_isleri.empty:
              formatted_u = format_table_df(u_isleri)
              st.dataframe(
                  formatted_u.drop(columns=["Seç"], errors="ignore"),
                  use_container_width=True,
                  hide_index=True,
              )
            else:
              st.info("Bu ustaya atanmış henüz kayıt bulunmuyor.")
      else:
        st.info("Sistemde kayıtlı usta bulunmamaktadır.")

    with tab_u2:
      col_add, col_del = st.columns(2)

      with col_add:
        st.subheader("➕ Yeni Usta Ekle")
        with st.form("yeni_usta_form", clear_on_submit=True):
          u_ad_soyad = st.text_input("Usta Adı Soyadı*")
          u_uzmanlik = st.text_input(
              "Uzmanlık Alanı", value="Doğalgaz & Tesisat"
          )
          u_tel = st.text_input("Telefon No")
          u_durum = st.selectbox("Durum", ["Aktif", "Pasif"])

          if st.form_submit_button("💾 Ustayı Kaydet", use_container_width=True):
            if u_ad_soyad.strip():
              try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum)"
                    " VALUES (?, ?, ?, ?)",
                    (u_ad_soyad.strip().upper(), u_uzmanlik, u_tel, u_durum),
                )
                conn.commit()
                st.success(f"✅ {u_ad_soyad} ustalar listesine eklendi!")
                st.rerun()
              except sqlite3.IntegrityError:
                st.error("Bu isimde bir usta zaten sistemde kayıtlı!")
            else:
              st.error("Usta adı boş bırakılamaz.")

      with col_del:
        st.subheader("🗑️ Usta Sil / Pasife Al")
        if not df_ustalar.empty:
          usta_dict = {
              f"{row['ad_soyad']} ({row['durum']})": row["id"]
              for _, row in df_ustalar.iterrows()
          }
          selected_usta_label = st.selectbox(
              "Silinecek Ustayı Seçin:", list(usta_dict.keys())
          )
          selected_usta_id = usta_dict[selected_usta_label]

          btn_u_pasif, btn_u_sil = st.columns(2)
          with btn_u_pasif:
            if st.button("🔴 Pasife Al", use_container_width=True):
              cursor = conn.cursor()
              cursor.execute(
                  "UPDATE ustalar SET durum='Pasif' WHERE id=?",
                  (selected_usta_id,),
              )
              conn.commit()
              st.warning("Usta pasife alındı!")
              st.rerun()
          with btn_u_sil:
            if st.button(
                "🔥 Veritabanından Tamamen Sil", use_container_width=True
            ):
              cursor = conn.cursor()
              cursor.execute("DELETE FROM ustalar WHERE id=?", (selected_usta_id,))
              conn.commit()
              st.error("Usta silindi!")
              st.rerun()

# ==========================================
# SAYFA 5: RAPORLAR, MALİ & USTA PERFORMANS ANALİZİ
# ==========================================
elif sayfa == "Raporlar & Analiz":
  st.title("📊 Ofis Detaylı Mali ve Usta Performans Analiz Paneli")

  if not izin_rapor_goruntule:
    st.warning("⚠️ Raporları görüntüleme yetkiniz bulunmamaktadır.")
  else:
    # Üst Kontroller (Periyot ve Ay Seçimi)
    st.markdown("##### 📅 Raporlama Periyodu Seçin:")
    periyot_tipi = st.radio(
        "Periyot", ["Aylık Raporlama", "Haftalık Raporlama"], horizontal=True
    )

    df_kayitlar = pd.read_sql_query(
        "SELECT * FROM kayitlar ORDER BY id DESC", conn
    )

    if not df_kayitlar.empty:
      # Mevcut ayları bulma (Örn: 2026-06)
      if "proje_ayi" in df_kayitlar.columns:
        mevcut_aylar = sorted(
            [
                str(x)
                for x in df_kayitlar["proje_ayi"].dropna().unique()
                if str(x).strip() != ""
            ],
            reverse=True,
        )
      else:
        mevcut_aylar = [datetime.now().strftime("%Y-%m")]

      if not mevcut_aylar:
        mevcut_aylar = [datetime.now().strftime("%Y-%m")]

      secilen_ayi = st.selectbox(
          "🔍 İncelemek İstediğiniz Mali Ayı Seçin:", mevcut_aylar
      )

      # Filtreleme
      if periyot_tipi == "Aylık Raporlama":
        df_filtered = df_kayitlar[df_kayitlar["proje_ayi"] == secilen_ayi]
      else:
        # Son 7 günlük filtre
        yedi_gun_once = (datetime.now() - timedelta(days=7)).strftime(
            "%Y-%m-%d"
        )
        df_filtered = df_kayitlar.copy()  # Basitleştirilmiş haftalık görünüm

      # Üst Özet Kartları
      m1, m2, m3 = st.columns(3)
      toplam_ciro = (
          df_filtered["toplam_bedel"].sum() if not df_filtered.empty else 0.0
      )
      toplam_tahsil = (
          df_filtered["alinan_tutar"].sum() if not df_filtered.empty else 0.0
      )
      kalan_alacak = (
          df_filtered["kalan_tutar"].sum() if not df_filtered.empty else 0.0
      )

      with m1:
        st.markdown(
            f'<div class="dashboard-card"><div class="card-value">🔥 Toplam'
            f" Ciro ({secilen_ayi})</div><div"
            f' class="card-value">₺{toplam_ciro:,.2f}</div></div>',
            unsafe_allow_html=True,
        )
      with m2:
        st.markdown(
            f'<div class="dashboard-card"><div class="card-value">✅ Toplam'
            f' Tahsil Edilen</div><div class="card-value"'
            f' style="color:#10b981;">₺{toplam_tahsil:,.2f}</div></div>',
            unsafe_allow_html=True,
        )
      with m3:
        st.markdown(
            f'<div class="dashboard-card"><div class="card-value">🚨 Kalan Ofis'
            f' Alacağı</div><div class="card-value"'
            f' style="color:#ef4444;">₺{kalan_alacak:,.2f}</div></div>',
            unsafe_allow_html=True,
        )

      st.markdown("<br>", unsafe_allow_html=True)
      st.subheader(
          f"📊 {secilen_ayi} Dönemi Usta Detaylı İş/İçerik Dağılım Sayıları"
      )

      # Yan yana düzen: Sol grafik, Sağ net adet tablosu
      grafik_col, tablo_col = st.columns([1, 1])

      # Usta bazlı özet tablo oluşturma
      ustalar_listesi = pd.read_sql_query(
          "SELECT ad_soyad FROM ustalar", conn
      )["ad_soyad"].tolist()
      # Veride geçen ekstra ustalar varsa ekle
      for u in df_filtered["usta_adi"].dropna().unique():
        if u not in ustalar_listesi:
          ustalar_listesi.append(u)

      summary_data = []
      for usta in ustalar_listesi:
        u_df = df_filtered[df_filtered["usta_adi"] == usta]
        toplam_is = len(u_df)
        kolon_toplam = (
            int(u_df["kolon_sayisi"].sum())
            if "kolon_sayisi" in u_df.columns
            else 0
        )
        ic_toplam = (
            int(u_df["ic_tesisat_sayisi"].sum())
            if "ic_tesisat_sayisi" in u_df.columns
            else 0
        )

        # Diğer işlemler sayımı
        cihaz_degisimi_sayisi = 0
        randevu_red_sayisi = 0
        if "diger_islemler" in u_df.columns:
          for val in u_df["diger_islemler"].dropna():
            if "Cihaz Değişimi" in str(val):
              cihaz_degisimi_sayisi += 1
            if "Randevu Reddi" in str(val):
              randevu_red_sayisi += 1

        urettigi_ciro = (
            float(u_df["toplam_bedel"].sum())
            if not u_df.empty
            else 0.0
        )

        summary_data.append({
            "Usta Adı": usta,
            "Toplam İş (Adet)": toplam_is,
            "Kolon Sayısı": kolon_toplam,
            "İç Tesisat Sayısı": ic_toplam,
            "Cihaz Değişimi": cihaz_degisimi_sayisi,
            "Randevu Reddi": randevu_red_sayisi,
            "Ürettiği Toplam Ciro (TL)": urettigi_ciro,
        })

      summary_df = pd.DataFrame(summary_data)
      summary_df = summary_df[
          summary_df["Toplam İş (Adet)"] > 0
      ]  # Sadece iş yapanlar

      with grafik_col:
        st.markdown("**📉 Ustaların Kolon ve İç Tesisat Dağılımı (Grafik)**")
        if not summary_df.empty:
          chart_df = summary_df.set_index("Usta Adı")[
              ["Kolon Sayısı", "İç Tesisat Sayısı"]
          ]
          st.bar_chart(chart_df)
        else:
          st.info("Bu dönem için grafik verisi bulunmuyor.")

      with tablo_col:
        st.markdown("**📋 Net Adet Raporlama Tablosu**")
        if not summary_df.empty:
          st.dataframe(
              summary_df, use_container_width=True, hide_index=True
          )
        else:
          st.info("Bu dönem için tablo verisi bulunmuyor.")

      st.markdown("---")
      st.subheader("📋 Detaylı Kayıt Raporu ve Düzenleme / Kaldırma Alanı")

      formatted_rapor_df = format_table_df(df_filtered)

      edited_rapor_df = st.data_editor(
          formatted_rapor_df,
          column_config={
              "Seç": st.column_config.CheckboxColumn("Seç", default=False),
              "Kolon Sayısı": st.column_config.NumberColumn(
                  "Kolon", min_value=0, step=1
              ),
              "İç Tesisat": st.column_config.NumberColumn(
                  "İç Tesisat", min_value=0, step=1
              ),
              "Toplam Bedel (TL)": st.column_config.NumberColumn(
                  "Toplam Bedel (TL)", min_value=0, format="%.2f"
              ),
              "Alınan Ödeme (TL)": st.column_config.NumberColumn(
                  "Alınan Ödeme (TL)", min_value=0, format="%.2f"
              ),
              "Kalan Alacak (TL)": st.column_config.NumberColumn(
                  "Kalan Alacak (TL)", disabled=True, format="%.2f"
              ),
              "Ödeme Tipi": st.column_config.SelectboxColumn(
                  "Ödeme Tipi",
                  options=[
                      "Nakit",
                      "Havale / EFT",
                      "Kredi Kartı",
                      "Ödeme Alınmadı",
                  ],
              ),
              "Armadaş Durumu": st.column_config.SelectboxColumn(
                  "Armadaş Durumu",
                  options=[
                      "Armadaş Dijital Onay Bekliyor",
                      "Onay Bekliyor",
                      "Armadaş Eksik / Red Aldı",
                      "Gaz Açıldı / Müşteriye Teslim Edildi",
                      "Randevu Alındı",
                  ],
              ),
          },
          use_container_width=True,
          hide_index=True,
          key="rapor_tablo_editor",
      )

      col_btn1, col_btn2 = st.columns(2)
      with col_btn1:
        if st.button(
            "💾 Rapor Tablosundaki Değişiklikleri Kaydet",
            type="primary",
            use_container_width=True,
        ):
          cursor = conn.cursor()
          for idx, row in edited_rapor_df.iterrows():
            rec_id = row["id"]
            t_bedel = float(row.get("Toplam Bedel (TL)", 0))
            a_odeme = float(row.get("Alınan Ödeme (TL)", 0))
            k_alacak = max(0.0, t_bedel - a_odeme)
            kolon_val = int(row.get("Kolon Sayısı", 0) or 0)
            ic_val = int(row.get("İç Tesisat", 0) or 0)

            cursor.execute(
                """
                            UPDATE kayitlar SET
                                proje_tarihi = ?, musteri_adi = ?, usta_adi = ?, kolon_sayisi = ?, ic_tesisat_sayisi = ?,
                                armadas_surec_adimi = ?, diger_islemler = ?, toplam_bedel = ?, alinan_tutar = ?, 
                                kalan_tutar = ?, odeme_yontemi = ?, sayac_seri_no = ?, notlar = ?
                            WHERE id = ?
                        """,
                (
                    str(row.get("Kayıt Tarihi", "")),
                    str(row.get("Müşteri Adı", "")),
                    str(row.get("Sorumlu Usta", "")),
                    kolon_val,
                    ic_val,
                    str(row.get("Armadaş Durumu", "")),
                    str(row.get("Diğer İşlemler", "")),
                    t_bedel,
                    a_odeme,
                    k_alacak,
                    str(row.get("Ödeme Tipi", "")),
                    str(row.get("Sayaç Seri No", "")),
                    str(row.get("Notlar", "")),
                    rec_id,
                ),
            )
          conn.commit()
          st.success("✅ Tüm güncellemeler veritabanına işlendi!")
          st.rerun()

      with col_btn2:
        if st.button(
            "🗑️ Seçili Raporları / Kayıtları Listeden Kaldır",
            type="secondary",
            use_container_width=True,
        ):
          secilenler = edited_rapor_df[edited_rapor_df["Seç"] == True]
          if not secilenler.empty:
            cursor = conn.cursor()
            for _, row in secilenler.iterrows():
              cursor.execute("DELETE FROM kayitlar WHERE id = ?", (row["id"],))
            conn.commit()
            st.warning(
                f"⚠️ Seçilen {len(secilenler)} kayıt rapordan ve sistemden"
                " kaldırıldı!"
            )
            st.rerun()
          else:
            st.info(
                "Lütfen kaldırmak için tablodan en az bir satırın 'Seç'"
                " kutucuğunu işaretleyin."
            )
    else:
      st.info("Sistemde raporlanacak kayıt bulunmuyor.")

# ==========================================
# SAYFA 6: KULLANICI ONAYLARI & İZİNLER
# ==========================================
elif sayfa == "Kullanıcı Onayları & İzinler":
  st.title("👥 Kullanıcı Onayları & Detaylı İzin Yönetimi")

  if not is_admin:
    st.warning("⚠️ Bu paneli görüntülemek için Yönetici yetkisine sahip olmalısınız.")
  else:
    df_kullanicilar = pd.read_sql_query(
        "SELECT * FROM kullanicilar ORDER BY id DESC", conn
    )

    if df_kullanicilar.empty:
      st.info("Sistemde kayıtlı kullanıcı bulunmuyor.")
    else:
      st.subheader("📋 Kayıtlı Kullanıcılar Listesi")
      st.dataframe(
          df_kullanicilar[[
              "id",
              "kullanici_adi",
              "ad_soyad",
              "telefon",
              "rol",
              "durum",
          ]],
          use_container_width=True,
          hide_index=True,
      )

      st.markdown("---")
      st.subheader("⚙️ Kullanıcı Onayı Yap ve Yetki / İzin Tanımla")

      user_opts = {
          f"#{row['id']} - {row['ad_soyad']} (@{row['kullanici_adi']})"
          f" [{row['durum']}]": row["id"]
          for _, row in df_kullanicilar.iterrows()
      }
      selected_user_label = st.selectbox(
          "Yetkilerini Düzenlemek İstediğiniz Kullanıcıyı Seçin:",
          list(user_opts.keys()),
      )
      selected_user_id = user_opts[selected_user_label]

      target_user = df_kullanicilar[
          df_kullanicilar["id"] == selected_user_id
      ].iloc[0]

      with st.form("kullanici_izin_formu"):
        c_u1, c_u2, c_u3 = st.columns(3)
        with c_u1:
          u_ad_soyad = st.text_input("Ad Soyad", value=str(target_user["ad_soyad"]))
          u_kullanici_adi = st.text_input(
              "Kullanıcı Adı",
              value=str(target_user["kullanici_adi"]),
              disabled=True,
          )
        with c_u2:
          rol_opts = ["Personel", "Yönetici"]
          u_rol = st.selectbox(
              "Rolü",
              rol_opts,
              index=rol_opts.index(target_user["rol"])
              if target_user["rol"] in rol_opts
              else 0,
          )
          durum_opts = ["Aktif", "Onay Bekliyor", "Pasif"]
          u_durum = st.selectbox(
              "Hesap Durumu",
              durum_opts,
              index=durum_opts.index(target_user["durum"])
              if target_user["durum"] in durum_opts
              else 0,
          )
        with c_u3:
          u_sifre = st.text_input(
              "Şifreyi Sıfırla / Değiştir", value=str(target_user["sifre"])
          )

        st.markdown("##### 🔑 Özel İzin Kutucukları")
        iz_col1, iz_col2, iz_col3 = st.columns(3)

        with iz_col1:
          i_kayit_ekle = st.checkbox(
              "➕ Yeni Kayıt Ekleme İzni",
              value=bool(target_user["izin_kayit_ekle"]),
          )
          i_kayit_duzenle = st.checkbox(
              "✏️ Kayıt Düzenleme İzni",
              value=bool(target_user["izin_kayit_duzenle"]),
          )
        with iz_col2:
          i_kayit_sil = st.checkbox(
              "🗑️ Kayıt Silme İzni", value=bool(target_user["izin_kayit_sil"])
          )
          i_usta_yonetim = st.checkbox(
              "🔧 Usta Yönetimi İzni",
              value=bool(target_user["izin_usta_yonetim"]),
          )
        with iz_col3:
          i_rapor = st.checkbox(
              "📊 Raporları Görüntüleme İzni",
              value=bool(target_user["izin_rapor_goruntule"]),
          )
          i_kullanici = st.checkbox(
              "👑 Kullanıcı & İzin Yönetimi İzni",
              value=bool(target_user["izin_kullanici_yonetim"]),
          )

        btn_u_col1, btn_u_col2 = st.columns([2, 1])
        with btn_u_col1:
          if st.form_submit_button(
              "💾 Yetki ve İzinleri Kaydet", use_container_width=True
          ):
            cursor = conn.cursor()
            cursor.execute(
                """
                            UPDATE kullanicilar SET
                                ad_soyad = ?, rol = ?, durum = ?, sifre = ?,
                                izin_kayit_ekle = ?, izin_kayit_duzenle = ?, izin_kayit_sil = ?,
                                izin_usta_yonetim = ?, izin_rapor_goruntule = ?, izin_kullanici_yonetim = ?
                            WHERE id = ?
                        """,
                (
                    u_ad_soyad,
                    u_rol,
                    u_durum,
                    u_sifre,
                    int(i_kayit_ekle),
                    int(i_kayit_duzenle),
                    int(i_kayit_sil),
                    int(i_usta_yonetim),
                    int(i_rapor),
                    int(i_kullanici),
                    selected_user_id,
                ),
            )
            conn.commit()
            st.success("✅ Kullanıcı izinleri başarıyla güncellendi!")
            st.rerun()
        with btn_u_col2:
          if target_user["kullanici_adi"] != "admin" and st.form_submit_button(
              "❌ Kullanıcıyı Sil", use_container_width=True
          ):
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM kullanicilar WHERE id = ?", (selected_user_id,)
            )
            conn.commit()
            st.warning("Kullanıcı sistemden silindi.")
            st.rerun()

conn.close()
