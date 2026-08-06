import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Güneş Doğalgaz - Servis Yönetim Sistemi",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VERİTABANI BAĞLANTISI VE TABLOLAR ---
def get_db():
    conn = sqlite3.connect("gunes_dogalgaz.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 1. Kayıtlar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS kayitlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seri_no TEXT,
                    musteri_adi TEXT,
                    telefon TEXT,
                    adres TEXT,
                    proje_tarihi TEXT,
                    proje_gelis_yolu TEXT,
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
                    regulator TEXT DEFAULT 'Yok',
                    notlar TEXT DEFAULT '',
                    durum TEXT
                )''')

    # 2. Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (
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
                )''')
    
    # --- MİGRASYON / EKSİK SÜTUN KONTROLLERİ ---
    c.execute("PRAGMA table_info(kayitlar)")
    kayitlar_sutunlar = [col[1] for col in c.fetchall()]
    if 'regulator' not in kayitlar_sutunlar:
        c.execute("ALTER TABLE kayitlar ADD COLUMN regulator TEXT DEFAULT 'Yok'")
    if 'notlar' not in kayitlar_sutunlar:
        c.execute("ALTER TABLE kayitlar ADD COLUMN notlar TEXT DEFAULT ''")

    c.execute("PRAGMA table_info(kullanicilar)")
    kullanici_sutunlar = [col[1] for col in c.fetchall()]
    
    sutun_eklemeleri = [
        ('telefon', "TEXT DEFAULT ''"),
        ('durum', "TEXT DEFAULT 'Aktif'"),
        ('rol', "TEXT DEFAULT 'Personel'"),
        ('izin_kayit_ekle', "INTEGER DEFAULT 1"),
        ('izin_kayit_duzenle', "INTEGER DEFAULT 1"),
        ('izin_kayit_sil', "INTEGER DEFAULT 0"),
        ('izin_usta_yonetim', "INTEGER DEFAULT 1"),
        ('izin_rapor_goruntule', "INTEGER DEFAULT 1"),
        ('izin_kullanici_yonetim', "INTEGER DEFAULT 0")
    ]
    
    for sutun_adi, sutun_tipi in sutun_eklemeleri:
        if sutun_adi not in kullanici_sutunlar:
            c.execute(f"ALTER TABLE kullanicilar ADD COLUMN {sutun_adi} {sutun_tipi}")

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
    else:
        c.execute("""
            UPDATE kullanicilar SET 
                rol='Yönetici', durum='Aktif',
                izin_kayit_ekle=1, izin_kayit_duzenle=1, izin_kayit_sil=1,
                izin_usta_yonetim=1, izin_rapor_goruntule=1, izin_kullanici_yonetim=1
            WHERE kullanici_adi='admin'
        """)
            
    conn.commit()
    conn.close()

init_db()

# --- CSS / TASARIM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0b101d; color: #f3f4f6; }
    [data-testid="stSidebar"] { background-color: #0d1424; border-right: 1px solid #1a233a; }
    
    .brand-container { display: flex; align-items: center; gap: 12px; margin-bottom: 25px; }
    .brand-icon {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        width: 42px; height: 42px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center; font-size: 22px;
    }
    .brand-title { font-weight: 700; font-size: 16px; color: #ffffff; }
    .brand-subtitle { font-size: 11px; color: #64748b; }

    .dashboard-card {
        background-color: #131c2e; border: 1px solid #1e2a45;
        border-radius: 14px; padding: 20px;
    }
    .card-value { font-size: 24px; font-weight: 700; color: #ffffff; }
    .card-label { font-size: 12px; color: #94a3b8; }
    
    .sidebar-user-box {
        margin-top: 20px; padding: 12px; background-color: #131c2e;
        border-radius: 12px; display: flex; align-items: center; gap: 12px;
        border: 1px solid #1e2a45;
    }
    .user-avatar {
        width: 38px; height: 38px; border-radius: 50%;
        background-color: #1e293b; color: #f59e0b; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        border: 1px solid #f59e0b;
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM (SESSION) KONTROLÜ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

conn = get_db()

# ==========================================
# EKRAN 0: GİRİŞ YAP / KAYIT OL
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align: center;'>
            <h1 style='color: #f59e0b;'>🔥 Güneş Doğalgaz</h1>
            <h3>Servis & Proje Yönetim Sistemi</h3>
        </div>
        """, unsafe_allow_html=True)
        
        tab_giris, tab_kayit = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
        
        with tab_giris:
            with st.form("login_form"):
                kullanici_adi = st.text_input("Kullanıcı Adı")
                sifre = st.text_input("Şifre", type="password")
                btn_login = st.form_submit_button("Giriş Yap", use_container_width=True)
                
                if btn_login:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, kullanici_adi, sifre, ad_soyad, telefon, rol, durum,
                               izin_kayit_ekle, izin_kayit_duzenle, izin_kayit_sil, 
                               izin_usta_yonetim, izin_rapor_goruntule, izin_kullanici_yonetim 
                        FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?
                    """, (kullanici_adi.strip(), sifre.strip()))
                    user = cursor.fetchone()
                    if user:
                        if user[6] != "Aktif":
                            st.error("⚠️ Hesabınız henüz onaylanmamıştır veya pasife alınmıştır.")
                        else:
                            st.session_state['logged_in'] = True
                            st.session_state['user_info'] = {
                                "id": user[0], "kullanici_adi": user[1], "ad_soyad": user[3],
                                "telefon": user[4], "rol": user[5], "durum": user[6],
                                "izin_kayit_ekle": bool(user[7]), "izin_kayit_duzenle": bool(user[8]),
                                "izin_kayit_sil": bool(user[9]), "izin_usta_yonetim": bool(user[10]),
                                "izin_rapor_goruntule": bool(user[11]), "izin_kullanici_yonetim": bool(user[12])
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
                btn_register = st.form_submit_button("Kayıt Başvurusu Yap", use_container_width=True)
                
                if btn_register and new_username and new_password:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, telefon, rol, durum)
                            VALUES (?, ?, ?, ?, 'Personel', 'Onay Bekliyor')
                        """, (new_username.strip(), new_password.strip(), new_ad_soyad.strip(), new_tel.strip()))
                        conn.commit()
                        st.success("✅ Kayıt başvurunuz alındı!")
                    except sqlite3.IntegrityError:
                        st.error("Bu kullanıcı adı zaten alınmış.")

    st.stop()

# --- İZİN KONTROLLERİ ---
user_info = st.session_state.get('user_info', {}) or {}
izin_kayit_ekle = user_info.get('izin_kayit_ekle', True)
izin_kayit_duzenle = user_info.get('izin_kayit_duzenle', True)
izin_kayit_sil = user_info.get('izin_kayit_sil', False)
izin_rapor_goruntule = user_info.get('izin_rapor_goruntule', True)
izin_kullanici_yonetim = user_info.get('izin_kullanici_yonetim', False)
is_admin = user_info.get('rol') == "Yönetici" or izin_kullanici_yonetim

# ==========================================
# SOL MENÜ (SIDEBAR) - USTALAR KALDIRILDI
# ==========================================
with st.sidebar:
    st.markdown("""
    <div class="brand-container">
        <div class="brand-icon">🔥</div>
        <div>
            <div class="brand-title">Güneş Doğalgaz</div>
            <div class="brand-subtitle">Servis Yönetim Sistemi</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # "Ustalar" kaldırıldı, yerine "Düzenleme" bölümü eklendi
    sayfa = st.radio(
        "", 
        ["Dashboard", "Kayıtlar", "Düzenleme", "Raporlar & Analiz", "Kullanıcı Onayları & İzinler"], 
        label_visibility="collapsed"
    )
    
    u_ad = user_info.get('ad_soyad', 'Kullanıcı')
    u_rol = user_info.get('rol', 'Personel')
    
    st.markdown(f"""
    <div class="sidebar-user-box">
        <div class="user-avatar">{u_ad[:2].upper() if u_ad else 'US'}</div>
        <div>
            <div style="font-size:13px; font-weight:600; color:#fff;">{u_ad}</div>
            <div style="font-size:11px; color:#f59e0b;">{u_rol}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.rerun()

# ==========================================
# YARDIMCI FONKSİYON: TABLO FORMATLAMA
# ==========================================
def format_table_df(df_input):
    """
    Görseldeki sütun yapısını birebir oluşturur (Proje İçeriği yok).
    """
    if df_input.empty:
        return pd.DataFrame(columns=[
            'Seç', 'Kayıt Tarihi', 'Müşteri Adı', 'Sorumlu Usta', 'Armadaş Durumu',
            'Toplam Bedel (TL)', 'Alınan Ödeme (TL)', 'Kalan Alacak (TL)', 'Ödeme Tipi',
            'Sayaç Seri No', 'Regülatör', 'Notlar', 'id'
        ])
    
    df = df_input.copy()
    if 'Seç' not in df.columns:
        df['Seç'] = False
        
    df_renamed = df.rename(columns={
        'proje_tarihi': 'Kayıt Tarihi',
        'musteri_adi': 'Müşteri Adı',
        'usta_adi': 'Sorumlu Usta',
        'armadas_surec_adimi': 'Armadaş Durumu',
        'toplam_bedel': 'Toplam Bedel (TL)',
        'alinan_tutar': 'Alınan Ödeme (TL)',
        'kalan_tutar': 'Kalan Alacak (TL)',
        'odeme_yontemi': 'Ödeme Tipi',
        'sayac_seri_no': 'Sayaç Seri No',
        'regulator': 'Regülatör',
        'notlar': 'Notlar'
    })
    
    sutun_sirasi = [
        'Seç', 'Kayıt Tarihi', 'Müşteri Adı', 'Sorumlu Usta', 'Armadaş Durumu',
        'Toplam Bedel (TL)', 'Alınan Ödeme (TL)', 'Kalan Alacak (TL)', 'Ödeme Tipi',
        'Sayaç Seri No', 'Regülatör', 'Notlar', 'id'
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

    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="dashboard-card"><div class="card-value">{len(df_kayitlar)}</div><div class="card-label">Toplam Proje</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_kayitlar["alinan_tutar"].sum() if not df_kayitlar.empty else 0:,.0f}</div><div class="card-label">Toplanan Alacak</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_kayitlar["kalan_tutar"].sum() if not df_kayitlar.empty else 0:,.0f}</div><div class="card-label">Bekleyen Ödeme</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="dashboard-card"><div class="card-value">{len(df_kayitlar[df_kayitlar["kalan_tutar"] > 0]) if not df_kayitlar.empty else 0}</div><div class="card-label">Borçlu Müşteri</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if (yeni_kayit_modal or st.session_state.get('form_acik', False)) and izin_kayit_ekle:
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Proje Kaydı Ekle", expanded=True):
            with st.form("yeni_kayit_formu", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    proje_tarihi = st.date_input("Kayıt Tarihi", datetime.now())
                    musteri_adi = st.text_input("Müşteri Adı*")
                    telefon = st.text_input("Telefon")
                    adres = st.text_area("Adres", height=68)
                    usta_adi = st.text_input("Sorumlu Usta", value="MEHMET BEKİROĞLU")

                with col_f2:
                    toplam_bedel = st.number_input("Toplam Bedel (TL)*", min_value=0.0, step=500.0)
                    alinan_tutar = st.number_input("Alınan Ödeme (TL)", min_value=0.0, step=500.0)
                    kalan_tutar_hesaplanan = max(0.0, toplam_bedel - alinan_tutar)
                    st.info(f"**Hesaplanan Kalan:** ₺{kalan_tutar_hesaplanan:,.2f}")
                    odeme_yontemi = st.selectbox("Ödeme Tipi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"])

                with col_f3:
                    armadas_surec_adimi = st.selectbox("Armadaş Durumu", ["Armadaş Dijital Onay Bekliyor", "Onay Bekliyor", "Armadaş Eksik / Red Aldı", "Gaz Açıldı / Müşteriye Teslim Edildi", "Randevu Alındı"])
                    sayac_seri_no = st.text_input("Sayaç Seri No")
                    regulator = st.selectbox("Regülatör", ["Var", "Yok"])
                    notlar = st.text_input("Notlar")

                if st.form_submit_button("💾 Kaydet") and musteri_adi.strip():
                    seri_no = f"GZ-{datetime.now().year}-{len(df_kayitlar) + 1:03d}"
                    durum = "Tamamlandı" if kalan_tutar_hesaplanan == 0 else "Devam Ediyor"
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO kayitlar (seri_no, musteri_adi, telefon, adres, proje_tarihi, usta_adi, 
                        armadas_surec_adimi, toplam_bedel, alinan_tutar, kalan_tutar, odeme_yontemi, sayac_seri_no, regulator, notlar, durum)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (seri_no, musteri_adi.strip(), telefon, adres, str(proje_tarihi), usta_adi, armadas_surec_adimi, toplam_bedel, alinan_tutar, kalan_tutar_hesaplanan, odeme_yontemi, sayac_seri_no, regulator, notlar, durum))
                    conn.commit()
                    st.success("Kayıt Başarılı!")
                    st.session_state['form_acik'] = False
                    st.rerun()

    st.subheader("Son Projeler")
    if not df_kayitlar.empty:
        formatted_df = format_table_df(df_kayitlar)
        st.dataframe(formatted_df.drop(columns=['Seç'], errors='ignore'), use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("📋 Tüm Kayıtlar")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    if not df_kayitlar.empty:
        formatted_df = format_table_df(df_kayitlar)
        st.dataframe(formatted_df.drop(columns=['Seç'], errors='ignore'), use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 3: YENİ DÜZENLEME BÖLÜMÜ (USTALAR YERİNE)
# ==========================================
elif sayfa == "Düzenleme":
    st.title("✏️ Proje & Kayıt Düzenleme Paneli")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    if df_kayitlar.empty:
        st.info("Düzenlenecek kayıt bulunamadı.")
    else:
        # Arama ve Seçim Alanı
        kayit_secenekleri = {
            f"#{row['id']} - {row['musteri_adi']} (Tarih: {row['proje_tarihi']} | Tel: {row['telefon']})": row['id']
            for _, row in df_kayitlar.iterrows()
        }
        
        selected_label = st.selectbox("🔍 Düzenlemek İstediğiniz Kaydı Seçin:", list(kayit_secenekleri.keys()))
        selected_id = kayit_secenekleri[selected_label]
        
        row_data = df_kayitlar[df_kayitlar['id'] == selected_id].iloc[0]
        
        st.markdown("---")
        st.subheader(f"🛠️ Müşteri: {row_data['musteri_adi']}")
        
        if not izin_kayit_duzenle:
            st.warning("⚠️ Kayıt düzenleme yetkiniz bulunmamaktadır.")
        else:
            with st.form("duzenleme_formu"):
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    e_musteri = st.text_input("Müşteri Adı", value=str(row_data['musteri_adi']))
                    e_tarih = st.text_input("Kayıt Tarihi", value=str(row_data['proje_tarihi']))
                    e_tel = st.text_input("Telefon", value=str(row_data['telefon'] or ''))
                    e_adres = st.text_area("Adres", value=str(row_data['adres'] or ''), height=68)
                
                with col_e2:
                    e_toplam = st.number_input("Toplam Bedel (TL)", value=float(row_data['toplam_bedel']), step=500.0)
                    e_alinan = st.number_input("Alınan Ödeme (TL)", value=float(row_data['alinan_tutar']), step=500.0)
                    e_kalan = max(0.0, e_toplam - e_alinan)
                    st.info(f"**Güncellenecek Kalan:** ₺{e_kalan:,.2f}")
                    
                    odeme_index = ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"].index(row_data['odeme_yontemi']) if row_data['odeme_yontemi'] in ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"] else 0
                    e_odeme_tipi = st.selectbox("Ödeme Tipi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"], index=odeme_index)

                with col_e3:
                    e_usta = st.text_input("Sorumlu Usta", value=str(row_data['usta_adi'] or ''))
                    
                    armadas_opts = ["Armadaş Dijital Onay Bekliyor", "Onay Bekliyor", "Armadaş Eksik / Red Aldı", "Gaz Açıldı / Müşteriye Teslim Edildi", "Randevu Alındı"]
                    arm_index = armadas_opts.index(row_data['armadas_surec_adimi']) if row_data['armadas_surec_adimi'] in armadas_opts else 0
                    e_armadas = st.selectbox("Armadaş Durumu", armadas_opts, index=arm_index)
                    
                    e_sayac = st.text_input("Sayaç Seri No", value=str(row_data['sayac_seri_no'] or ''))
                    e_regulator = st.selectbox("Regülatör", ["Var", "Yok"], index=0 if row_data['regulator'] == "Var" else 1)
                    e_notlar = st.text_input("Notlar", value=str(row_data['notlar'] or ''))

                btn_col1, btn_col2 = st.columns([2, 1])
                with btn_col1:
                    if st.form_submit_button("💾 Değişiklikleri Kaydet", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE kayitlar SET 
                                musteri_adi=?, proje_tarihi=?, telefon=?, adres=?,
                                toplam_bedel=?, alinan_tutar=?, kalan_tutar=?, odeme_yontemi=?,
                                usta_adi=?, armadas_surec_adimi=?, sayac_seri_no=?, regulator=?, notlar=?
                            WHERE id=?
                        """, (e_musteri, e_tarih, e_tel, e_adres, e_toplam, e_alinan, e_kalan, e_odeme_tipi, e_usta, e_armadas, e_sayac, e_regulator, e_notlar, selected_id))
                        conn.commit()
                        st.success("✅ Kayıt başarıyla güncellendi!")
                        st.rerun()
                with btn_col2:
                    if izin_kayit_sil and st.form_submit_button("🗑️ Kaydı Sil", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM kayitlar WHERE id=?", (selected_id,))
                        conn.commit()
                        st.warning("⚠️ Kayıt silindi!")
                        st.rerun()

# ==========================================
# SAYFA 4: RAPORLAR VE ANALİZ (DÜZENLEME EKLENDİ)
# ==========================================
elif sayfa == "Raporlar & Analiz":
    st.title("📊 Raporlar & Mali Analiz")
    
    if not izin_rapor_goruntule:
        st.warning("⚠️ Raporları görüntüleme yetkiniz bulunmamaktadır.")
    else:
        # Filtreleme
        col_r1, col_r2 = st.columns([2, 2])
        with col_r1:
            zaman_periyodu = st.selectbox("📅 Periyot Seçin", ["Tüm Zamanlar", "Bu Hafta (Son 7 Gün)", "Bu Ay (Son 30 Gün)"])
        with col_r2:
            arama_seri = st.text_input("🔍 Müşteri Adı / Seri No İle Filtrele", value="")

        df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
        
        if not df_kayitlar.empty:
            df_filtered = df_kayitlar.copy()
            
            if arama_seri.strip():
                df_filtered = df_filtered[
                    df_filtered['seri_no'].str.contains(arama_seri, case=False, na=False) |
                    df_filtered['musteri_adi'].str.contains(arama_seri, case=False, na=False)
                ]

            # Özet Kartları
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="dashboard-card"><div class="card-value">{len(df_filtered)}</div><div class="card-label">Raporlanan Proje</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_filtered["toplam_bedel"].sum():,.0f}</div><div class="card-label">Toplam Ciro</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_filtered["alinan_tutar"].sum():,.0f}</div><div class="card-label">Tahsil Edilen</div></div>', unsafe_allow_html=True)
            with m4: st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_filtered["kalan_tutar"].sum():,.0f}</div><div class="card-label">Kalan Alacak</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📋 Rapor Tablosu (Doğrudan Düzenlenebilir)")
            st.caption("✏️ Tablo hücrelerine çift tıklayarak bilgileri değiştirebilir, **'Seç'** kutusu ile satır bazlı hızlı form düzenlemesi yapabilirsiniz.")

            formatted_rapor_df = format_table_df(df_filtered)
            
            # DÜZENLENEBİLİR TABLO
            edited_rapor_df = st.data_editor(
                formatted_rapor_df,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                    "Toplam Bedel (TL)": st.column_config.NumberColumn("Toplam Bedel (TL)", min_value=0, format="%.2f"),
                    "Alınan Ödeme (TL)": st.column_config.NumberColumn("Alınan Ödeme (TL)", min_value=0, format="%.2f"),
                    "Kalan Alacak (TL)": st.column_config.NumberColumn("Kalan Alacak (TL)", disabled=True, format="%.2f"),
                    "Regülatör": st.column_config.SelectboxColumn("Regülatör", options=["Var", "Yok"]),
                    "Ödeme Tipi": st.column_config.SelectboxColumn("Ödeme Tipi", options=["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"]),
                    "Armadaş Durumu": st.column_config.SelectboxColumn("Armadaş Durumu", options=[
                        "Armadaş Dijital Onay Bekliyor", "Onay Bekliyor", "Armadaş Eksik / Red Aldı",
                        "Gaz Açıldı / Müşteriye Teslim Edildi", "Randevu Alındı"
                    ])
                },
                use_container_width=True,
                hide_index=True,
                key="rapor_tablo_editor"
            )

            # Tablodan doğrudan toplu kaydetme butonu
            if st.button("💾 Rapor Tablosundaki Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True):
                cursor = conn.cursor()
                for idx, row in edited_rapor_df.iterrows():
                    rec_id = row['id']
                    t_bedel = float(row.get('Toplam Bedel (TL)', 0))
                    a_odeme = float(row.get('Alınan Ödeme (TL)', 0))
                    k_alacak = max(0.0, t_bedel - a_odeme)
                    
                    cursor.execute("""
                        UPDATE kayitlar SET
                            proje_tarihi = ?,
                            musteri_adi = ?,
                            usta_adi = ?,
                            armadas_surec_adimi = ?,
                            toplam_bedel = ?,
                            alinan_tutar = ?,
                            kalan_tutar = ?,
                            odeme_yontemi = ?,
                            sayac_seri_no = ?,
                            regulator = ?,
                            notlar = ?
                        WHERE id = ?
                    """, (
                        str(row.get('Kayıt Tarihi', '')),
                        str(row.get('Müşteri Adı', '')),
                        str(row.get('Sorumlu Usta', '')),
                        str(row.get('Armadaş Durumu', '')),
                        t_bedel,
                        a_odeme,
                        k_alacak,
                        str(row.get('Ödeme Tipi', '')),
                        str(row.get('Sayaç Seri No', '')),
                        str(row.get('Regülatör', 'Yok')),
                        str(row.get('Notlar', '')),
                        rec_id
                    ))
                conn.commit()
                st.success("✅ Rapor tablosundaki tüm güncellemeler kaydedildi!")
                st.rerun()

            # Seçili Satırı Form ile Hızlı Düzenleme
            selected_rows = edited_rapor_df[edited_rapor_df['Seç'] == True]
            if not selected_rows.empty:
                selected_id = selected_rows.iloc[0]['id']
                r_data = df_kayitlar[df_kayitlar['id'] == selected_id].iloc[0]
                
                st.markdown("---")
                st.subheader(f"⚡ Seçili Kaydı Hızlı Düzenle: {r_data['musteri_adi']}")
                
                with st.form("rapor_secili_duzenle_form"):
                    rc1, rc2, rc3 = st.columns(3)
                    with rc1:
                        rf_musteri = st.text_input("Müşteri Adı", value=r_data['musteri_adi'])
                        rf_tarih = st.text_input("Kayıt Tarihi", value=r_data['proje_tarihi'])
                    with rc2:
                        rf_toplam = st.number_input("Toplam Bedel (TL)", value=float(r_data['toplam_bedel']))
                        rf_alinan = st.number_input("Alınan Ödeme (TL)", value=float(r_data['alinan_tutar']))
                    with rc3:
                        rf_usta = st.text_input("Sorumlu Usta", value=r_data['usta_adi'])
                        rf_notlar = st.text_input("Notlar", value=r_data['notlar'])
                    
                    if st.form_submit_button("💾 Kaydı Güncelle"):
                        cursor = conn.cursor()
                        rf_kalan = max(0.0, rf_toplam - rf_alinan)
                        cursor.execute("""
                            UPDATE kayitlar SET musteri_adi=?, proje_tarihi=?, toplam_bedel=?, alinan_tutar=?, kalan_tutar=?, usta_adi=?, notlar=? WHERE id=?
                        """, (rf_musteri, rf_tarih, rf_toplam, rf_alinan, rf_kalan, rf_usta, rf_notlar, selected_id))
                        conn.commit()
                        st.success("Güncellendi!")
                        st.rerun()
        else:
            st.info("Raporlanacak veri bulunmuyor.")

# ==========================================
# SAYFA 5: KULLANICI ONAYLARI
# ==========================================
elif sayfa == "Kullanıcı Onayları & İzinler":
    st.title("👥 Kullanıcı Yetki & İzin Yönetimi")
    if is_admin:
        df_kullanicilar = pd.read_sql_query("SELECT * FROM kullanicilar", conn)
        st.dataframe(df_kullanicilar[['id', 'kullanici_adi', 'ad_soyad', 'rol', 'durum']], use_container_width=True)
    else:
        st.warning("⚠️ Yetkiniz bulunmamaktadır.")

conn.close()
