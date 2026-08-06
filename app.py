import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from fpdf import FPDF
import io

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
                    durum TEXT
                )''')

    # 2. Ustalar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS ustalar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_soyad TEXT UNIQUE,
                    uzmanlik TEXT,
                    telefon TEXT,
                    durum TEXT
                )''')

    # 3. Kullanıcılar Tablosu
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
    
    # --- OTOMATİK VERİTABANI MİGRASYONU VE SÜTUN KONTROLLERİ ---
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

    # Admin Hesabını Oluştur / Yetkilerini Tamamla
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
        
    c.execute("SELECT COUNT(*) FROM ustalar")
    if c.fetchone()[0] == 0:
        varsayilan_ustalar = [
            ("MEHMET BEKİROĞLU", "Doğalgaz Tesisatı", "0532 111 2233", "Aktif"),
            ("VATAN SİNAN", "Kombi & Tesisat", "0533 222 3344", "Aktif"),
            ("SURİYELİ MUHAMMET", "İç Tesisat", "0534 333 4455", "Aktif")
        ]
        for usta in varsayilan_ustalar:
            try:
                c.execute("INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum) VALUES (?, ?, ?, ?)", usta)
            except sqlite3.IntegrityError:
                pass
            
    conn.commit()
    conn.close()

init_db()

# --- YARDIMCI BİLGİ İŞLEME FONKSİYONLARI ---
def format_proje_icerigi(kolon, ic_tesisat):
    """Kolon ve İç Tesisat sayılarından Proje İçeriği metnini oluşturur."""
    try:
        kolon = int(kolon) if kolon else 0
        ic_tesisat = int(ic_tesisat) if ic_tesisat else 0
    except ValueError:
        kolon, ic_tesisat = 0, 0
        
    parcalar = []
    if kolon > 0:
        parcalar.append(f"{kolon} Kolon")
    if ic_tesisat > 0:
        parcalar.append(f"{ic_tesisat} İç Tesisat")
        
    return ", ".join(parcalar) if parcalar else "Tesisat Belirtilmedi"

def prepare_dataframe(df):
    """Veri çerçevesine Proje İçeriği sütununu ekler."""
    if not df.empty and 'kolon_sayisi' in df.columns and 'ic_tesisat_sayisi' in df.columns:
        df['proje_icerigi'] = df.apply(lambda r: format_proje_icerigi(r.get('kolon_sayisi', 0), r.get('ic_tesisat_sayisi', 0)), axis=1)
    elif not df.empty:
        df['proje_icerigi'] = "-"
    return df

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

# --- TÜRKÇE KARAKTER DÜZELTİCİLİ PDF ---
def tr_fix(text):
    if not text: return ""
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisouCGISOU")
    return str(text).translate(tr_map)

def generate_usta_pdf(usta_adi, df_usta):
    df_usta = prepare_dataframe(df_usta)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(190, 10, tr_fix(f"Gunes Dogalgaz - Usta Raporu: {usta_adi}"), ln=True, align='C')
    pdf.ln(6)
    
    # Sütun Başlıkları
    pdf.set_font("Helvetica", 'B', 8)
    pdf.cell(20, 7, tr_fix("Tarih"), 1)
    pdf.cell(42, 7, tr_fix("Musteri"), 1)
    pdf.cell(38, 7, tr_fix("Proje Icerigi"), 1)  # <--- PROJE İÇERİĞİ SÜTUNU
    pdf.cell(26, 7, tr_fix("Alinan (TL)"), 1)
    pdf.cell(26, 7, tr_fix("Kalan (TL)"), 1)
    pdf.cell(38, 7, tr_fix("Armadas Durumu"), 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", '', 8)
    for _, row in df_usta.iterrows():
        pdf.cell(20, 7, tr_fix(str(row.get('proje_tarihi', ''))), 1)
        pdf.cell(42, 7, tr_fix(str(row.get('musteri_adi', ''))[:22]), 1)
        pdf.cell(38, 7, tr_fix(str(row.get('proje_icerigi', ''))[:20]), 1) # <--- PROJE İÇERİĞİ DEĞERİ
        pdf.cell(26, 7, f"{row.get('alinan_tutar', 0):,.2f}", 1)
        pdf.cell(26, 7, f"{row.get('kalan_tutar', 0):,.2f}", 1)
        pdf.cell(38, 7, tr_fix(str(row.get('armadas_surec_adimi', '-'))[:20]), 1)
        pdf.ln()
        
    return pdf.output()

# --- OTURUM (SESSION) KONTROLÜ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

conn = get_db()

# ==========================================
# EKRAN 0: GİRİŞ YAP / KAYIT OL / GÖZ AT
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
        
        tab_giris, tab_kayit, tab_gozat = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol", "👀 Hizmet & Fiyat Listesi"])
        
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
                            st.error("⚠️ Hesabınız henüz yönetici tarafından onaylanmamıştır veya pasife alınmıştır.")
                        else:
                            st.session_state['logged_in'] = True
                            st.session_state['user_info'] = {
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
                                "izin_kullanici_yonetim": bool(user[12])
                            }
                            st.success(f"Hoş geldiniz, {user[3]}!")
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
                
                if btn_register:
                    if new_username and new_password and new_ad_soyad and new_tel:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO kullanicilar (
                                    kullanici_adi, sifre, ad_soyad, telefon, rol, durum,
                                    izin_kayit_ekle, izin_kayit_duzenle, izin_kayit_sil,
                                    izin_usta_yonetim, izin_rapor_goruntule, izin_kullanici_yonetim
                                ) VALUES (?, ?, ?, ?, 'Personel', 'Onay Bekliyor', 1, 1, 0, 1, 1, 0)
                            """, (new_username.strip(), new_password.strip(), new_ad_soyad.strip(), new_tel.strip()))
                            conn.commit()
                            st.success("✅ Kayıt başvurunuz alındı! Yönetici onayladıktan sonra giriş yapabilirsiniz.")
                        except sqlite3.IntegrityError:
                            st.error("Bu kullanıcı adı zaten alınmış.")
                    else:
                        st.warning("Lütfen tüm alanları doldurun.")

        with tab_gozat:
            st.info("ℹ️ Genel hizmet ve referans proje bilgileri (Salt-okunur).")
            df_kayitlar_public = prepare_dataframe(pd.read_sql_query("SELECT seri_no, kolon_sayisi, ic_tesisat_sayisi, armadas_surec_adimi, toplam_bedel, durum FROM kayitlar LIMIT 10", conn))
            if not df_kayitlar_public.empty:
                st.subheader("📋 Referans Projeler")
                st.dataframe(df_kayitlar_public[['seri_no', 'proje_icerigi', 'armadas_surec_adimi', 'toplam_bedel', 'durum']], use_container_width=True, hide_index=True)

    st.stop()

# ==========================================
# SOL MENÜ (SIDEBAR) & HESAP SİLME
# ==========================================
user_info = st.session_state['user_info']
is_admin = user_info['rol'] == "Yönetici" or user_info['izin_kullanici_yonetim']

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
    
    sayfa_secenekleri = ["Dashboard", "Kayıtlar", "Ustalar", "Raporlar & Analiz", "Kullanıcı Onayları & İzinler"]
    sayfa = st.radio("", sayfa_secenekleri, label_visibility="collapsed")
    
    st.markdown(f"""
    <div class="sidebar-user-box">
        <div class="user-avatar">{user_info['ad_soyad'][:2].upper()}</div>
        <div>
            <div style="font-size:13px; font-weight:600; color:#fff;">{user_info['ad_soyad']}</div>
            <div style="font-size:11px; color:#f59e0b;">{user_info['rol']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("⚙️ Hesabım & Güvenlik"):
        st.write(f"**Kullanıcı Adı:** {user_info['kullanici_adi']}")
        st.write(f"**Telefon:** {user_info['telefon']}")
        st.markdown("---")
        st.caption("🚨 **Hesabımı Sil:** Bu işlem hesabınızı sistemden kalıcı olarak siler.")
        
        confirm_delete = st.checkbox("Hesabımı kalıcı olarak silmek istiyorum", key="confirm_self_del")
        if st.button("💥 Hesabımı Sil", use_container_width=True, disabled=not confirm_delete):
            if user_info['kullanici_adi'] == 'admin':
                st.error("⚠️ Ana sistem yönetici (admin) hesabı silinemez!")
            else:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM kullanicilar WHERE id=?", (user_info['id'],))
                conn.commit()
                st.session_state['logged_in'] = False
                st.session_state['user_info'] = None
                st.success("Hesabınız silindi.")
                st.rerun()

    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.rerun()

# ==========================================
# SAYFA 1: DASHBOARD
# ==========================================
if sayfa == "Dashboard":
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title("Merkezi İş Takip Ekranı")
        st.caption(f"Hoş geldiniz, **{user_info['ad_soyad']}** ({user_info['rol']})")
    with col_head2:
        st.write("")
        if user_info['izin_kayit_ekle']:
            yeni_kayit_modal = st.button("➕ Yeni Proje Kaydı", use_container_width=True)
        else:
            yeni_kayit_modal = False
            st.info("ℹ️ Yeni Kayıt İzniniz Bulunmuyor")

    df_kayitlar = prepare_dataframe(pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn))
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar WHERE durum='Aktif'", conn)
    
    toplam_kayit = len(df_kayitlar)
    toplam_alinan = df_kayitlar['alinan_tutar'].sum() if not df_kayitlar.empty else 0
    toplam_kalan = df_kayitlar['kalan_tutar'].sum() if not df_kayitlar.empty else 0
    aktif_usta = len(df_ustalar)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="dashboard-card"><div class="card-value">{toplam_kayit}</div><div class="card-label">Toplam Proje</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{toplam_alinan:,.0f}</div><div class="card-label">Toplanan Alacak</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{toplam_kalan:,.0f}</div><div class="card-label">Bekleyen Ödeme</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="dashboard-card"><div class="card-value">{aktif_usta}</div><div class="card-label">Aktif Usta</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if (yeni_kayit_modal or st.session_state.get('form_acik', False)) and user_info['izin_kayit_ekle']:
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Proje Kaydı Ekle", expanded=True):
            with st.form("yeni_kayit_formu", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    proje_tarihi = st.date_input("Proje Tarihi", datetime.now())
                    musteri_adi = st.text_input("Müşteri / Proje Adı*")
                    telefon = st.text_input("Telefon")
                    adres = st.text_area("Adres", height=68)
                    proje_gelis_yolu = st.selectbox("Geliş Yolu", ["WhatsApp", "Ofis", "Telefon", "Referans"])
                    ustalar_listesi = df_ustalar['ad_soyad'].tolist() if not df_ustalar.empty else ["Usta Atanmadı"]
                    usta_adi = st.selectbox("Atanan Usta", ustalar_listesi)

                with col_f2:
                    toplam_bedel = st.number_input("Toplam Bedel (TL)*", min_value=0.0, step=500.0)
                    alinan_tutar = st.number_input("Alınan Ödeme (TL)", min_value=0.0, step=500.0)
                    kalan_tutar_hesaplanan = max(0.0, toplam_bedel - alinan_tutar)
                    st.info(f"**Hesaplanan Kalan:** ₺{kalan_tutar_hesaplanan:,.2f}")
                    odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Ödeme Alınmadı"])

                with col_f3:
                    kolon_sayisi = st.number_input("Kolon Sayısı", min_value=0, value=1)
                    ic_tesisat_sayisi = st.number_input("İç Tesisat Sayısı", min_value=0, value=1)
                    armadas_surec_adimi = st.selectbox("Armadaş Süreci", ["Armadaş Dijital Onay Bekliyor", "Onay Bekliyor", "Armadaş Eksik / Red Aldı", "Gaz Açıldı / Müşteriye Teslim Edildi", "Randevu Alındı"])
                    sayac_seri_no = st.text_input("Sayaç Seri No")

                btn_kaydet = st.form_submit_button("💾 Kaydet")
                if btn_kaydet and musteri_adi.strip():
                    seri_no = f"GZ-{datetime.now().year}-{toplam_kayit + 1:03d}"
                    durum = "Tamamlandı" if kalan_tutar_hesaplanan == 0 else "Devam Ediyor"
                    
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO kayitlar (seri_no, musteri_adi, telefon, adres, proje_tarihi, proje_gelis_yolu, 
                        usta_adi, kolon_sayisi, ic_tesisat_sayisi, armadas_surec_adimi, toplam_bedel, alinan_tutar, kalan_tutar, odeme_yontemi, sayac_seri_no, durum)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (seri_no, musteri_adi.strip(), telefon, adres, str(proje_tarihi), proje_gelis_yolu, usta_adi, kolon_sayisi, ic_tesisat_sayisi, armadas_surec_adimi, toplam_bedel, alinan_tutar, kalan_tutar_hesaplanan, odeme_yontemi, sayac_seri_no, durum))
                    conn.commit()
                    st.success("Kayıt Başarılı!")
                    st.session_state['form_acik'] = False
                    st.rerun()

    st.subheader("Son Projeler")
    if not df_kayitlar.empty:
        # Sütun isimleri görseldeki başlıklar ile tam uyumlu hale getirildi
        df_display = df_kayitlar[['proje_tarihi', 'musteri_adi', 'proje_icerigi', 'usta_adi', 'armadas_surec_adimi', 'toplam_bedel', 'alinan_tutar', 'kalan_tutar', 'odeme_yontemi', 'sayac_seri_no']].copy()
        df_display.columns = ['Kayıt Tarihi', 'Müşteri Adı', 'Proje İçeriği', 'Sorumlu Usta', 'Armadaş Durumu', 'Toplam Bedel (TL)', 'Alınan Ödeme (TL)', 'Kalan Alacak (TL)', 'Ödeme Tipi', 'Sayaç Seri No']
        st.dataframe(df_display, use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("Tüm Proje Kayıtları")
    df_kayitlar = prepare_dataframe(pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn))
    
    if not df_kayitlar.empty:
        for idx, row in df_kayitlar.iterrows():
            with st.expander(f"📌 {row['seri_no']} - {row['musteri_adi']} | 📐 Proje İçeriği: {row['proje_icerigi']} (Kalan: ₺{row['kalan_tutar']:,.2f})"):
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.write(f"**Proje İçeriği:** {row['proje_icerigi']}")
                    st.write(f"**Telefon:** {row['telefon']}")
                    st.write(f"**Adres:** {row['adres']}")
                    st.write(f"**Sorumlu Usta:** {row['usta_adi']}")
                    st.write(f"**Armadaş Durumu:** {row['armadas_surec_adimi']}")
                with col_k2:
                    st.write(f"**Toplam Bedel:** ₺{row['toplam_bedel']:,.2f}")
                    st.write(f"**Alınan Tutar:** ₺{row['alinan_tutar']:,.2f}")
                    st.write(f"**Ödeme Yöntemi:** {row['odeme_yontemi']}")
                    st.write(f"**Sayaç Seri No:** {row['sayac_seri_no']}")
                    
                    if user_info['izin_kayit_sil']:
                        if st.button("🗑️ Kaydı Sil", key=f"del_rec_{row['id']}"):
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM kayitlar WHERE id=?", (row['id'],))
                            conn.commit()
                            st.warning("Proje kaydı silindi!")
                            st.rerun()

# ==========================================
# SAYFA 3: USTALAR
# ==========================================
elif sayfa == "Ustalar":
    st.title("Usta Yönetim Paneli")
    
    if user_info['izin_usta_yonetim']:
        tab_usta_liste, tab_usta_ekle = st.tabs(["👥 Usta Listesi & Proje Detayları", "➕ Yeni Usta Ekle"])
        
        with tab_usta_ekle:
            with st.form("yeni_usta_form", clear_on_submit=True):
                y_ad = st.text_input("Usta Adı Soyadı*")
                y_uzmanlik = st.text_input("Uzmanlık / Alanı", "Doğalgaz Tesisatı")
                y_tel = st.text_input("Telefon")
                y_durum = st.selectbox("Durum", ["Aktif", "Pasif"])
                btn_u_ekle = st.form_submit_button("Ustayı Kaydet")
                
                if btn_u_ekle and y_ad.strip():
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum) VALUES (?, ?, ?, ?)",
                                       (y_ad.strip(), y_uzmanlik, y_tel, y_durum))
                        conn.commit()
                        st.success(f"'{y_ad}' başarıyla eklendi!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bu usta ismi zaten mevcut!")
    else:
        tab_usta_liste = st.container()
        st.info("ℹ️ Usta ekleme/düzenleme yetkiniz bulunmamaktadır. Sadece liste görüntülenmektedir.")

    with tab_usta_liste:
        df_ustalar = pd.read_sql_query("SELECT * FROM ustalar", conn)
        df_kayitlar = prepare_dataframe(pd.read_sql_query("SELECT * FROM kayitlar", conn))
        
        if not df_ustalar.empty:
            for idx, usta in df_ustalar.iterrows():
                u_isleri = df_kayitlar[df_kayitlar['usta_adi'] == usta['ad_soyad']] if not df_kayitlar.empty else pd.DataFrame()
                
                with st.expander(f"🔧 {usta['ad_soyad']} ({usta['durum']}) - Telefon: {usta['telefon']} | Toplam Proje: {len(u_isleri)}"):
                    col_u_detay, col_u_duzenle = st.columns([1.2, 0.8])
                    
                    with col_u_detay:
                        st.write(f"**Uzmanlık:** {usta['uzmanlik']}")
                        
                        if not u_isleri.empty:
                            st.markdown("##### 📐 Üstlendiği Projeler ve İçerikleri")
                            df_u_show = u_isleri[['proje_tarihi', 'musteri_adi', 'proje_icerigi', 'armadas_surec_adimi', 'kalan_tutar']].copy()
                            df_u_show.columns = ['Tarih', 'Müşteri', 'Proje İçeriği', 'Armadaş Durumu', 'Kalan Alacak']
                            st.dataframe(df_u_show, use_container_width=True, hide_index=True)
                            
                            pdf_bytes = generate_usta_pdf(usta['ad_soyad'], u_isleri)
                            st.download_button(
                                label="📄 Usta İş & Proje İçeriği Raporunu İndir (PDF)",
                                data=bytes(pdf_bytes),
                                file_name=f"{usta['ad_soyad']}_proje_raporu.pdf",
                                mime="application/pdf",
                                key=f"pdf_btn_{usta['id']}"
                            )
                        else:
                            st.info("Bu ustaya henüz atanmış bir proje bulunmuyor.")
                    
                    with col_u_duzenle:
                        if user_info['izin_usta_yonetim']:
                            with st.form(key=f"edit_usta_{usta['id']}"):
                                e_ad = st.text_input("Ad Soyad", value=usta['ad_soyad'])
                                e_uzmanlik = st.text_input("Uzmanlık", value=usta['uzmanlik'])
                                e_tel = st.text_input("Telefon", value=usta['telefon'])
                                e_durum = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if usta['durum']=="Aktif" else 1)
                                
                                c_btn1, c_btn2 = st.columns(2)
                                with c_btn1:
                                    btn_guncelle = st.form_submit_button("💾 Güncelle")
                                with c_btn2:
                                    btn_sil = st.form_submit_button("🗑️ Ustayı Sil")
                                    
                                if btn_guncelle:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE ustalar SET ad_soyad=?, uzmanlik=?, telefon=?, durum=? WHERE id=?",
                                                   (e_ad, e_uzmanlik, e_tel, e_durum, usta['id']))
                                    conn.commit()
                                    st.success("Usta güncellendi!")
                                    st.rerun()
                                    
                                if btn_sil:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM ustalar WHERE id=?", (usta['id'],))
                                    conn.commit()
                                    st.warning("Usta silindi!")
                                    st.rerun()

# ==========================================
# SAYFA 4: RAPORLAR VE ANALİZ
# ==========================================
elif sayfa == "Raporlar & Analiz":
    st.title("📊 Mali & Dönemsel Raporlama")
    
    if not user_info['izin_rapor_goruntule']:
        st.warning("⚠️ Raporları ve mali analizleri görüntüleme yetkiniz bulunmamaktadır.")
    else:
        df_kayitlar = prepare_dataframe(pd.read_sql_query("SELECT * FROM kayitlar", conn))
        if df_kayitlar.empty:
            st.info("Raporlama yapılacak henüz bir proje kaydı bulunmuyor.")
        else:
            df_kayitlar['proje_tarihi_dt'] = pd.to_datetime(df_kayitlar['proje_tarihi'], errors='coerce')
            
            zaman_filtresi = st.selectbox(
                "📅 Raporlama Periyodu Seçin",
                ["Bu Hafta (Son 7 Gün)", "Bu Ay (Son 30 Gün)", "Tüm Zamanlar"]
            )
            
            bugun = datetime.now().date()
            if zaman_filtresi == "Bu Hafta (Son 7 Gün)":
                baslangic_tarihi = bugun - timedelta(days=7)
            elif zaman_filtresi == "Bu Ay (Son 30 Gün)":
                baslangic_tarihi = bugun - timedelta(days=30)
            else:
                baslangic_tarihi = pd.to_datetime(df_kayitlar['proje_tarihi_dt']).min().date()

            df_filtered = df_kayitlar[df_kayitlar['proje_tarihi_dt'].dt.date >= baslangic_tarihi]

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f'<div class="dashboard-card"><div class="card-value">{len(df_filtered)}</div><div class="card-label">Dönemdeki Proje Sayısı</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_filtered["toplam_bedel"].sum():,.0f}</div><div class="card-label">Dönem Cirosu</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_filtered["alinan_tutar"].sum():,.0f}</div><div class="card-label">Tahsil Edilen</div></div>', unsafe_allow_html=True)
            with m4:
                st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{df_filtered["kalan_tutar"].sum():,.0f}</div><div class="card-label">Kalan Alacak</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            df_rep_display = df_filtered[['seri_no', 'proje_tarihi', 'musteri_adi', 'proje_icerigi', 'usta_adi', 'toplam_bedel', 'kalan_tutar']].copy()
            df_rep_display.columns = ['Seri No', 'Tarih', 'Müşteri', 'Proje İçeriği', 'Usta', 'Toplam Bedel', 'Kalan Alacak']
            st.dataframe(df_rep_display, use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 5: KULLANICI ONAYLARI VE İZİN AYARLARI
# ==========================================
elif sayfa == "Kullanıcı Onayları & İzinler":
    st.title("👥 Kullanıcı Yetki & İzin Yönetimi")
    st.write(f"Mevcut Kullanıcı: **{user_info['ad_soyad']}** ({user_info['rol']})")
    
    if is_admin:
        st.markdown("---")
        tab_onay, tab_kullanicilar_izin = st.tabs(["⏳ Onay Bekleyen Başvurular", "🔑 Kullanıcı İzin Paneli & Yetkilendirme"])
        
        with tab_onay:
            df_bekleyenler = pd.read_sql_query("SELECT id, kullanici_adi, ad_soyad, telefon, rol, durum FROM kullanicilar WHERE durum='Onay Bekliyor'", conn)
            
            if df_bekleyenler.empty:
                st.success("🎉 Şu anda onay bekleyen üyelik başvurusu bulunmuyor.")
            else:
                for idx, k_user in df_bekleyenler.iterrows():
                    col_b1, col_b2, col_b3, col_b4 = st.columns([2, 2, 1, 1])
                    with col_b1:
                        st.write(f"**{k_user['ad_soyad']}** (@{k_user['kullanici_adi']})")
                    with col_b2:
                        st.write(f"📞 {k_user['telefon']}")
                    with col_b3:
                        if st.button("✅ Onayla (Aktif Yap)", key=f"app_btn_{k_user['id']}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("UPDATE kullanicilar SET durum='Aktif' WHERE id=?", (k_user['id'],))
                            conn.commit()
                            st.success(f"{k_user['ad_soyad']} onaylandı!")
                            st.rerun()
                    with col_b4:
                        if st.button("❌ Reddet / Sil", key=f"rej_btn_{k_user['id']}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM kullanicilar WHERE id=?", (k_user['id'],))
                            conn.commit()
                            st.warning("Başvuru silindi!")
                            st.rerun()
                    st.markdown("---")

        with tab_kullanicilar_izin:
            df_kullanicilar = pd.read_sql_query("""
                SELECT id, kullanici_adi, ad_soyad, telefon, rol, durum,
                       izin_kayit_ekle, izin_kayit_duzenle, izin_kayit_sil,
                       izin_usta_yonetim, izin_rapor_goruntule, izin_kullanici_yonetim
                FROM kullanicilar
            """, conn)
            
            for idx, k_user in df_kullanicilar.iterrows():
                is_self_admin = k_user['kullanici_adi'] == 'admin'
                
                with st.expander(f"👤 {k_user['ad_soyad']} (@{k_user['kullanici_adi']}) - Rol: {k_user['rol']} | Durum: {k_user['durum']}"):
                    
                    st.markdown("##### ⚡ Hızlı Ana İzin Tuşları")
                    col_master1, col_master2, col_master3 = st.columns([1, 1, 2])
                    
                    with col_master1:
                        if st.button("🟢 Tüm İzinleri Ver", key=f"btn_all_on_{k_user['id']}", disabled=is_self_admin, use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE kullanicilar SET 
                                    izin_kayit_ekle=1, izin_kayit_duzenle=1, izin_kayit_sil=1,
                                    izin_usta_yonetim=1, izin_rapor_goruntule=1, izin_kullanici_yonetim=1
                                WHERE id=?
                            """, (k_user['id'],))
                            conn.commit()
                            st.success(f"{k_user['ad_soyad']} kullanıcısına tüm yetkiler verildi!")
                            st.rerun()
                            
                    with col_master2:
                        if st.button("🔴 Tüm İzinleri Kaldır", key=f"btn_all_off_{k_user['id']}", disabled=is_self_admin, use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE kullanicilar SET 
                                    izin_kayit_ekle=0, izin_kayit_duzenle=0, izin_kayit_sil=0,
                                    izin_usta_yonetim=0, izin_rapor_goruntule=0, izin_kullanici_yonetim=0
                                WHERE id=?
                            """, (k_user['id'],))
                            conn.commit()
                            st.warning(f"{k_user['ad_soyad']} kullanıcısının tüm yetkileri kaldırıldı!")
                            st.rerun()
                            
                    st.markdown("---")
                    
                    with st.form(key=f"permissions_form_{k_user['id']}"):
                        st.markdown("##### 🛠️ Detaylı Modül İzinleri")
                        
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            chk_ekle = st.checkbox("➕ Proje Kaydı Ekleme", value=bool(k_user['izin_kayit_ekle']), disabled=is_self_admin)
                            chk_duzenle = st.checkbox("✏️ Proje Güncelleme / Düzenleme", value=bool(k_user['izin_kayit_duzenle']), disabled=is_self_admin)
                            chk_sil = st.checkbox("🗑️ Proje Silme Yetkisi", value=bool(k_user['izin_kayit_sil']), disabled=is_self_admin)
                        
                        with col_p2:
                            chk_usta = st.checkbox("🔧 Usta Yönetimi (Ekle/Düzenle/Sil)", value=bool(k_user['izin_usta_yonetim']), disabled=is_self_admin)
                            chk_rapor = st.checkbox("📊 Rapor ve Analizleri Görme", value=bool(k_user['izin_rapor_goruntule']), disabled=is_self_admin)
                            chk_kullanici = st.checkbox("👥 Kullanıcı & İzin Yönetimi", value=bool(k_user['izin_kullanici_yonetim']), disabled=is_self_admin)

                        st.markdown("---")
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            rol_opts = ["Yönetici", "Yönetici Yardımcısı", "Personel"]
                            yeni_rol = st.selectbox("Atanan Rol", rol_opts, index=rol_opts.index(k_user['rol']) if k_user['rol'] in rol_opts else 2, disabled=is_self_admin)
                        with col_r2:
                            durum_opts = ["Aktif", "Pasif", "Onay Bekliyor"]
                            yeni_durum = st.selectbox("Erişim Durumu", durum_opts, index=durum_opts.index(k_user['durum']) if k_user['durum'] in durum_opts else 0, disabled=is_self_admin)

                        st.markdown("<br>", unsafe_allow_html=True)
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            btn_save_perm = st.form_submit_button("💾 İzinleri Ve Kullanıcıyı Güncelle", disabled=is_self_admin, use_container_width=True)
                        with btn_col2:
                            btn_del_user = st.form_submit_button("🗑️ Kullanıcıyı Sistemden Çıkar / Sil", disabled=is_self_admin, use_container_width=True)

                        if btn_save_perm:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE kullanicilar SET 
                                    rol=?, durum=?,
                                    izin_kayit_ekle=?, izin_kayit_duzenle=?, izin_kayit_sil=?,
                                    izin_usta_yonetim=?, izin_rapor_goruntule=?, izin_kullanici_yonetim=?
                                WHERE id=?
                            """, (
                                yeni_rol, yeni_durum,
                                int(chk_ekle), int(chk_duzenle), int(chk_sil),
                                int(chk_usta), int(chk_rapor), int(chk_kullanici),
                                k_user['id']
                            ))
                            conn.commit()
                            st.success(f"{k_user['ad_soyad']} için güncellemeler kaydedildi!")
                            st.rerun()

                        if btn_del_user:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM kullanicilar WHERE id=?", (k_user['id'],))
                            conn.commit()
                            st.warning(f"{k_user['ad_soyad']} sistemden çıkarıldı!")
                            st.rerun()
    else:
        st.warning("⚠️ Bu sayfadaki kullanıcı izinlerini yönetme yetkiniz bulunmamaktadır.")

conn.close()
