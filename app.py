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
                    durum TEXT
                )''')
    
    # --- OTOMATİK VERİTABANI MİGRASYONU (HATA ENGELLECİ) ---
    c.execute("PRAGMA table_info(kullanicilar)")
    kullanici_sutunlar = [col[1] for col in c.fetchall()]
    if 'telefon' not in kullanici_sutunlar:
        c.execute("ALTER TABLE kullanicilar ADD COLUMN telefon TEXT DEFAULT ''")
    if 'durum' not in kullanici_sutunlar:
        c.execute("ALTER TABLE kullanicilar ADD COLUMN durum TEXT DEFAULT 'Aktif'")

    # Varsayılan Admin Hesabı
    c.execute("SELECT COUNT(*) FROM kullanicilar WHERE kullanici_adi = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, telefon, rol, durum) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", "1234", "Yönetici Anıl", "05000000000", "Yönetici", "Aktif"))
        
    c.execute("SELECT COUNT(*) FROM ustalar")
    if c.fetchone()[0] == 0:
        varsayilan_ustalar = [
            ("Mehmet Usta", "Doğalgaz Tesisatı", "0532 111 2233", "Aktif"),
            ("Ali Usta", "Kombi & Kazan", "0533 222 3344", "Aktif")
        ]
        for usta in varsayilan_ustalar:
            try:
                c.execute("INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum) VALUES (?, ?, ?, ?)", usta)
            except sqlite3.IntegrityError:
                pass
            
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

# --- TÜRKÇE KARAKTER DÜZELTİCİLİ PDF ---
def tr_fix(text):
    if not text: return ""
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisouCGISOU")
    return str(text).translate(tr_map)

def generate_usta_pdf(usta_adi, df_usta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 15)
    pdf.cell(190, 10, tr_fix(f"Gunes Dogalgaz - Usta Raporu: {usta_adi}"), ln=True, align='C')
    pdf.ln(8)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(25, 7, tr_fix("Tarih"), 1)
    pdf.cell(55, 7, tr_fix("Musteri"), 1)
    pdf.cell(35, 7, tr_fix("Alinan (TL)"), 1)
    pdf.cell(35, 7, tr_fix("Kalan (TL)"), 1)
    pdf.cell(40, 7, tr_fix("Armadas Durumu"), 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", '', 8)
    for _, row in df_usta.iterrows():
        pdf.cell(25, 7, tr_fix(str(row.get('proje_tarihi', ''))), 1)
        pdf.cell(55, 7, tr_fix(str(row.get('musteri_adi', ''))[:24]), 1)
        pdf.cell(35, 7, f"{row.get('alinan_tutar', 0):,.2f}", 1)
        pdf.cell(35, 7, f"{row.get('kalan_tutar', 0):,.2f}", 1)
        pdf.cell(40, 7, tr_fix(str(row.get('armadas_surec_adimi', '-'))[:20]), 1)
        pdf.ln()
        
    return pdf.output()

# --- OTURUM (SESSION) KONTROLÜ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

conn = get_db()

# ==========================================
# EKRAN 0: GİRİŞ YAP / KAYIT OL / GÖZ AT (MİSAFİR)
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
        
        tab_giris, tab_kayit, tab_gozat = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol", "👀 Hizmet & Fiyat Listesi (Göz At)"])
        
        # TAB 1: GİRİŞ YAP
        with tab_giris:
            with st.form("login_form"):
                kullanici_adi = st.text_input("Kullanıcı Adı")
                sifre = st.text_input("Şifre", type="password")
                btn_login = st.form_submit_button("Giriş Yap", use_container_width=True)
                
                if btn_login:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?", (kullanici_adi.strip(), sifre.strip()))
                    user = cursor.fetchone()
                    if user:
                        # [0]id, [1]kullanici_adi, [2]sifre, [3]ad_soyad, [4]telefon, [5]rol, [6]durum
                        if user[6] != "Aktif":
                            st.error("⚠️ Hesabınız henüz yönetici tarafından onaylanmamıştır veya pasife alınmıştır.")
                        else:
                            st.session_state['logged_in'] = True
                            st.session_state['user_info'] = {
                                "id": user[0],
                                "kullanici_adi": user[1],
                                "ad_soyad": user[3],
                                "telefon": user[4],
                                "rol": user[5]
                            }
                            st.success(f"Hoş geldiniz, {user[3]}!")
                            st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı!")
                        
        # TAB 2: KAYIT OL
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
                                INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, telefon, rol, durum) 
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (new_username.strip(), new_password.strip(), new_ad_soyad.strip(), new_tel.strip(), "Personel", "Onay Bekliyor"))
                            conn.commit()
                            st.success("✅ Kayıt başvurunuz alındı! Yönetici onayladıktan sonra giriş yapabilirsiniz.")
                        except sqlite3.IntegrityError:
                            st.error("Bu kullanıcı adı zaten alınmış.")
                    else:
                        st.warning("Lütfen tüm alanları doldurun.")

        # TAB 3: MİSAFİR MODU
        with tab_gozat:
            st.info("ℹ️ Bu alanda genel hizmet ve referans proje bilgileri salt-okunur olarak görüntülenmektedir.")
            df_kayitlar_public = pd.read_sql_query("SELECT seri_no, armadas_surec_adimi, toplam_bedel, durum FROM kayitlar LIMIT 10", conn)
            if not df_kayitlar_public.empty:
                st.subheader("📋 Referans Projeler ve Süreçler")
                st.dataframe(df_kayitlar_public, use_container_width=True, hide_index=True)
            else:
                st.write("Henüz yayınlanmış genel bir proje kaydı bulunmuyor.")

    st.stop()

# ==========================================
# SOL MENÜ (SIDEBAR) & OTURUM KARTI
# ==========================================
user_info = st.session_state['user_info']
is_admin_or_assistant = user_info['rol'] in ["Yönetici", "Yönetici Yardımcısı"]

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
    
    sayfa_secenekleri = ["Dashboard", "Kayıtlar", "Ustalar", "Raporlar & Analiz", "Kullanıcı Onayları & Ayarlar"]
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
        st.title("Dashboard")
        st.caption(f"Hoş geldiniz, **{user_info['ad_soyad']}** ({user_info['rol']})")
    with col_head2:
        st.write("")
        yeni_kayit_modal = st.button("➕ Yeni Proje Kaydı", use_container_width=True)

    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
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

    if yeni_kayit_modal or st.session_state.get('form_acik', False):
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Proje & Fiyat Kaydı Ekle", expanded=True):
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
                    odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı"])

                with col_f3:
                    kolon_sayisi = st.number_input("Kolon Sayısı", min_value=0)
                    ic_tesisat_sayisi = st.number_input("İç Tesisat Sayısı", min_value=0)
                    armadas_surec_adimi = st.selectbox("Armadaş Süreci", ["Çizim Aşamasında", "Onay Bekliyor", "Onaylandı", "Randevu Alındı", "Gaz Açıldı", "Eksik/Red"])
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
        st.dataframe(df_kayitlar[['seri_no', 'musteri_adi', 'usta_adi', 'armadas_surec_adimi', 'toplam_bedel', 'kalan_tutar']], use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("Tüm Proje Kayıtları")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    st.dataframe(df_kayitlar, use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 3: USTALAR
# ==========================================
elif sayfa == "Ustalar":
    st.title("Usta Yönetim Paneli")
    tab_usta_liste, tab_usta_ekle = st.tabs(["👥 Usta Listesi & İşlemler", "➕ Yeni Usta Ekle"])
    
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

    with tab_usta_liste:
        df_ustalar = pd.read_sql_query("SELECT * FROM ustalar", conn)
        df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
        
        if not df_ustalar.empty:
            for idx, usta in df_ustalar.iterrows():
                u_isleri = df_kayitlar[df_kayitlar['usta_adi'] == usta['ad_soyad']] if not df_kayitlar.empty else pd.DataFrame()
                
                with st.expander(f"🔧 {usta['ad_soyad']} ({usta['durum']}) - Telefon: {usta['telefon']}"):
                    col_u_detay, col_u_duzenle = st.columns([1, 1])
                    
                    with col_u_detay:
                        st.write(f"**Uzmanlık:** {usta['uzmanlik']}")
                        st.write(f"**Toplam Üstlendiği İş:** {len(u_isleri)}")
                        if not u_isleri.empty:
                            pdf_bytes = generate_usta_pdf(usta['ad_soyad'], u_isleri)
                            st.download_button(
                                label="📄 Usta İş Raporunu İndir (PDF)",
                                data=bytes(pdf_bytes),
                                file_name=f"{usta['ad_soyad']}_rapor.pdf",
                                mime="application/pdf",
                                key=f"pdf_btn_{usta['id']}"
                            )
                    
                    with col_u_duzenle:
                        if is_admin_or_assistant:
                            st.markdown("##### ✏️ Usta Bilgilerini Güncelle")
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
                        else:
                            st.warning("Düzenleme yetkiniz yok.")
        else:
            st.info("Kayıtlı usta bulunamadı.")

# ==========================================
# SAYFA 4: RAPORLAR VE ZAMAN BAZLI ANALİZLER (YENİ EKLEME)
# ==========================================
elif sayfa == "Raporlar & Analiz":
    st.title("📊 Mali & Dönemsel Raporlama")
    
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    if df_kayitlar.empty:
        st.info("Raporlama yapılacak henüz bir proje kaydı bulunmuyor.")
    else:
        # Tarih formatını pandas datetime'a çevir
        df_kayitlar['proje_tarihi_dt'] = pd.to_datetime(df_kayitlar['proje_tarihi'], errors='coerce')
        
        # Filtre Seçenekleri
        col_r1, col_r2 = st.columns([2, 2])
        with col_r1:
            zaman_filtresi = st.selectbox(
                "📅 Raporlama Periyodu Seçin",
                ["Bu Hafta (Son 7 Gün)", "Bu Ay (Son 30 Gün)", "Tüm Zamanlar", "Özel Tarih Aralığı"]
            )
        
        bugun = datetime.now().date()
        
        if zaman_filtresi == "Bu Hafta (Son 7 Gün)":
            baslangic_tarihi = bugun - timedelta(days=7)
            bitis_tarihi = bugun
        elif zaman_filtresi == "Bu Ay (Son 30 Gün)":
            baslangic_tarihi = bugun - timedelta(days=30)
            bitis_tarihi = bugun
        elif zaman_filtresi == "Özel Tarih Aralığı":
            with col_r2:
                tarih_araligi = st.date_input("Tarih Aralığı", [bugun - timedelta(days=30), bugun])
                if len(tarih_araligi) == 2:
                    baslangic_tarihi, bitis_tarihi = tarih_araligi[0], tarih_araligi[1]
                else:
                    baslangic_tarihi, bitis_tarihi = bugun - timedelta(days=30), bugun
        else:
            baslangic_tarihi = pd.to_datetime(df_kayitlar['proje_tarihi_dt']).min().date()
            bitis_tarihi = bugun

        # Filtre Uygulama
        df_filtered = df_kayitlar[
            (df_kayitlar['proje_tarihi_dt'].dt.date >= baslangic_tarihi) & 
            (df_kayitlar['proje_tarihi_dt'].dt.date <= bitis_tarihi)
        ]

        st.markdown("---")
        
        # Özet Metrik Kartları
        m1, m2, m3, m4 = st.columns(4)
        r_proje_sayisi = len(df_filtered)
        r_toplam_bedel = df_filtered['toplam_bedel'].sum()
        r_toplam_alinan = df_filtered['alinan_tutar'].sum()
        r_toplam_kalan = df_filtered['kalan_tutar'].sum()

        with m1:
            st.markdown(f'<div class="dashboard-card"><div class="card-value">{r_proje_sayisi}</div><div class="card-label">Dönemdeki Proje Sayısı</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{r_toplam_bedel:,.0f}</div><div class="card-label">Dönem Cirosu / Bedel</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{r_toplam_alinan:,.0f}</div><div class="card-label">Tahsil Edilen</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="dashboard-card"><div class="card-value">₺{r_toplam_kalan:,.0f}</div><div class="card-label">Kalan Alacak</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Görsel Grafikler & Detaylar
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            st.subheader("📈 Günlük / Dönemsel Ciro Trendi")
            if not df_filtered.empty:
                chart_data = df_filtered.groupby('proje_tarihi')['toplam_bedel'].sum().reset_index()
                chart_data = chart_data.set_index('proje_tarihi')
                st.bar_chart(chart_data)
            else:
                st.write("Seçilen tarih aralığında veri yok.")

        with col_g2:
            st.subheader("🔧 Usta Bazlı İş Dağılımı")
            if not df_filtered.empty:
                usta_dist = df_filtered['usta_adi'].value_counts()
                st.dataframe(usta_dist, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Seçilen Döneme Ait Proje Listesi")
        st.dataframe(df_filtered[['seri_no', 'proje_tarihi', 'musteri_adi', 'usta_adi', 'toplam_bedel', 'alinan_tutar', 'kalan_tutar', 'armadas_surec_adimi']], use_container_width=True, hide_index=True)

        # Excel İndirme Butonları
        st.markdown("---")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtered.drop(columns=['proje_tarihi_dt'], errors='ignore').to_excel(writer, index=False, sheet_name='Filtrelenmis Rapor')
            df_kayitlar.drop(columns=['proje_tarihi_dt'], errors='ignore').to_excel(writer, index=False, sheet_name='Tum Kayitlar')
        
        st.download_button(
            label="📊 Seçilen Dönem Raporunu Excel Olarak İndir",
            data=output.getvalue(),
            file_name=f"gunes_dogalgaz_rapor_{baslangic_tarihi}_ile_{bitis_tarihi}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==========================================
# SAYFA 5: KULLANICI ONAYLARI VE İZİN AYARLARI
# ==========================================
elif sayfa == "Kullanıcı Onayları & Ayarlar":
    st.title("👥 Kullanıcı Yetki & Onay Yönetimi")
    st.write(f"Mevcut Oturum: **{user_info['ad_soyad']}** ({user_info['rol']})")
    
    if is_admin_or_assistant:
        st.markdown("---")
        df_kullanicilar = pd.read_sql_query("SELECT id, kullanici_adi, ad_soyad, telefon, rol, durum FROM kullanicilar", conn)
        
        st.subheader("📋 Kayıtlı Kullanıcılar ve İzinler")
        
        for idx, k_user in df_kullanicilar.iterrows():
            is_self = k_user['kullanici_adi'] == user_info['kullanici_adi']
            
            with st.expander(f"👤 {k_user['ad_soyad']} (@{k_user['kullanici_adi']}) - Rol: {k_user['rol']} | Durum: {k_user['durum']}"):
                with st.form(key=f"edit_user_form_{k_user['id']}"):
                    col_u1, col_u2, col_u3 = st.columns(3)
                    
                    with col_u1:
                        st.write(f"**Telefon:** {k_user['telefon']}")
                        st.write(f"**Kullanıcı Adı:** {k_user['kullanici_adi']}")
                    
                    with col_u2:
                        rol_index = 0 if k_user['rol'] == "Yönetici" else (1 if k_user['rol'] == "Yönetici Yardımcısı" else 2)
                        yeni_rol = st.selectbox("Atanan Rol", ["Yönetici", "Yönetici Yardımcısı", "Personel"], index=rol_index, disabled=is_self)
                        
                    with col_u3:
                        durum_list = ["Onay Bekliyor", "Aktif", "Pasif"]
                        durum_index = durum_list.index(k_user['durum']) if k_user['durum'] in durum_list else 0
                        yeni_durum = st.selectbox("Erişim Durumu", durum_list, index=durum_index, disabled=is_self)

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        btn_u_kaydet = st.form_submit_button("💾 Değişiklikleri Kaydet", disabled=is_self)
                    with col_b2:
                        btn_u_sil = st.form_submit_button("🗑️ Kullanıcıyı Sil", disabled=is_self)

                    if btn_u_kaydet:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE kullanicilar SET rol=?, durum=? WHERE id=?", (yeni_rol, yeni_durum, k_user['id']))
                        conn.commit()
                        st.success(f"{k_user['ad_soyad']} kullanıcısının bilgileri güncellendi!")
                        st.rerun()

                    if btn_u_sil:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM kullanicilar WHERE id=?", (k_user['id'],))
                        conn.commit()
                        st.warning(f"{k_user['ad_soyad']} silindi!")
                        st.rerun()
    else:
        st.warning("⚠️ Bu sayfadaki kullanıcı izinlerini yönetme yetkiniz bulunmamaktadır.")

conn.close()
