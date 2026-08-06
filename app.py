import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
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
    
    # Kayıtlar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS kayitlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seri_no TEXT,
                    musteri_adi TEXT,
                    telefon TEXT,
                    adres TEXT,
                    proje_tarihi TEXT,
                    proje_gelis_yolu TEXT,
                    usta_adi TEXT,
                    kolon_sayisi INTEGER,
                    ic_tesisat_sayisi INTEGER,
                    diger_islemler TEXT,
                    armadas_surec_adimi TEXT,
                    eksik_red_nedeni TEXT,
                    toplam_bedel REAL,
                    alinan_tutar REAL,
                    kalan_tutar REAL,
                    odeme_yontemi TEXT,
                    sayac_seri_no TEXT,
                    regulator_durumu TEXT,
                    durum TEXT
                )''')
                
    # Var olan veritabanında eksik sütunlar varsa ekle (Migration)
    mevcut_sutunlar = [row[1] for row in c.execute("PRAGMA table_info(kayitlar)").fetchall()]
    yeni_sutunlar = {
        "proje_gelis_yolu": "TEXT",
        "kolon_sayisi": "INTEGER DEFAULT 0",
        "ic_tesisat_sayisi": "INTEGER DEFAULT 0",
        "diger_islemler": "TEXT",
        "armadas_surec_adimi": "TEXT",
        "eksik_red_nedeni": "TEXT",
        "toplam_bedel": "REAL DEFAULT 0.0",
        "sayac_seri_no": "TEXT",
        "regulator_durumu": "TEXT"
    }
    for sutun, tip in yeni_sutunlar.items():
        if sutun not in mevcut_sutunlar:
            c.execute(f"ALTER TABLE kayitlar ADD COLUMN {sutun} {tip}")

    # Ustalar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS ustalar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_soyad TEXT UNIQUE,
                    uzmanlik TEXT,
                    telefon TEXT,
                    durum TEXT
                )''')
    
    # Varsayılan Ustaları Ekle
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

# --- PREMİUM GELİŞMİŞ KOYU TEMA (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Ana Arka Plan */
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    
    /* Sol Menü (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* Kompakt Özet Kartları */
    .metric-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-card.accent-orange { border-left: 4px solid #f59e0b; }
    .metric-card.accent-green { border-left: 4px solid #10b981; }
    .metric-card.accent-yellow { border-left: 4px solid #eab308; }
    .metric-card.accent-blue { border-left: 4px solid #3b82f6; }
    
    .metric-title { 
        color: #9ca3af; 
        font-size: 11px; 
        font-weight: 600; 
        letter-spacing: 0.5px;
        text-transform: uppercase; 
    }
    .metric-value { 
        font-size: 22px; 
        font-weight: 700; 
        margin: 2px 0; 
    }
    .metric-sub { font-size: 11px; font-weight: 500; }
    
    /* Metin Renkleri */
    .text-green { color: #10b981; }
    .text-yellow { color: #f59e0b; }
    .text-blue { color: #60a5fa; }
    
    /* Usta Kompakt Kart Yapısı */
    .usta-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .usta-stats {
        display: flex;
        justify-content: space-between;
        background-color: #192233;
        padding: 8px 10px;
        border-radius: 6px;
        margin-top: 10px;
        font-size: 12px;
    }

    /* Durum Rozetleri */
    .badge {
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-success { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-danger { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }

    /* Buton Tasarımları */
    .stButton>button {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: #000000;
        font-weight: 600;
        border-radius: 6px;
        border: none;
        padding: 6px 16px;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.4);
        color: #000;
    }
    
    /* Input & Select Box Düzenlemeleri */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        border-radius: 6px !important;
        background-color: #111827 !important;
        border: 1px solid #374151 !important;
        color: #f3f4f6 !important;
    }
    
    /* Expander Çerçeveleri */
    .streamlit-expanderHeader {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 6px !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- PDF OLUŞTURUCU ---
def generate_usta_pdf(usta_adi, df_usta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 15)
    pdf.cell(190, 10, f"Gunes Dogalgaz - Usta Raporu: {usta_adi}", ln=True, align='C')
    pdf.ln(8)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(25, 7, "Tarih", 1)
    pdf.cell(55, 7, "Musteri", 1)
    pdf.cell(35, 7, "Alinan (TL)", 1)
    pdf.cell(35, 7, "Kalan (TL)", 1)
    pdf.cell(40, 7, "Armadas Durumu", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", '', 8)
    for _, row in df_usta.iterrows():
        pdf.cell(25, 7, str(row['proje_tarihi']), 1)
        pdf.cell(55, 7, str(row['musteri_adi'])[:24], 1)
        pdf.cell(35, 7, f"{row['alinan_tutar']:,.2f}", 1)
        pdf.cell(35, 7, f"{row['kalan_tutar']:,.2f}", 1)
        pdf.cell(40, 7, str(row.get('armadas_surec_adimi', '-'))[:20], 1)
        pdf.ln()
        
    return pdf.output()

# --- SOL MENÜ (SIDEBAR) ---
with st.sidebar:
    st.markdown("### 🔥 Güneş Doğalgaz")
    st.caption("Servis & Proje Yönetimi")
    st.markdown("---")
    
    sayfa = st.radio(
        "📌 MENÜ",
        ["Dashboard", "Kayıtlar", "Ustalar", "Raporlar", "Ayarlar"]
    )
    
    st.markdown("---")
    st.markdown("👤 **Yönetici Panel**")
    st.caption("admin@gunesdogalgaz.com")

conn = get_db()

# ==========================================
# SAYFA 1: DASHBOARD
# ==========================================
if sayfa == "Dashboard":
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title("Dashboard")
        st.caption("Genel durum özetleri ve hızlı proje girişi")
    with col_head2:
        st.write("")
        yeni_kayit_modal = st.button("➕ Yeni Proje Kaydı", use_container_width=True)

    # Verileri Çek
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar WHERE durum='Aktif'", conn)
    
    toplam_kayit = len(df_kayitlar)
    toplam_alinan = df_kayitlar['alinan_tutar'].sum() if not df_kayitlar.empty else 0
    toplam_kalan = df_kayitlar['kalan_tutar'].sum() if not df_kayitlar.empty else 0
    aktif_usta = len(df_ustalar)

    # 4'lü Kompakt Kart Grubu
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card accent-blue">
            <div class="metric-title">Toplam Proje</div>
            <div class="metric-value">{toplam_kayit}</div>
            <div class="metric-sub text-blue">Kayıtlı İş Sayısı</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card accent-green">
            <div class="metric-title">Tahsil Edilen</div>
            <div class="metric-value text-green">₺{toplam_alinan:,.0f}</div>
            <div class="metric-sub text-green">Alınan Toplam Kapora</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card accent-yellow">
            <div class="metric-title">Bekleyen Alacak</div>
            <div class="metric-value text-yellow">₺{toplam_kalan:,.0f}</div>
            <div class="metric-sub text-yellow">Kalan Toplam Bakiye</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card accent-orange">
            <div class="metric-title">Aktif Usta</div>
            <div class="metric-value">{aktif_usta}</div>
            <div class="metric-sub text-blue">Sahadaki Usta</div>
        </div>
        """, unsafe_allow_html=True)

    # FORM PANELERİ (Ekrana Tam Uyumlu)
    if yeni_kayit_modal or st.session_state.get('form_acik', False):
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Proje Kaydı Ekle", expanded=True):
            with st.form("yeni_kayit_formu", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    st.markdown("##### 📌 Genel Bilgiler")
                    proje_tarihi = st.date_input("Proje / Kayıt Tarihi", datetime.now())
                    musteri_adi = st.text_input("Müşteri / Proje Adı*")
                    telefon = st.text_input("Müşteri Telefonu")
                    adres = st.text_area("Adres / Konum", height=68)
                    proje_gelis_yolu = st.selectbox("Proje Geliş Yolu", ["WhatsApp", "Ofis / Yüz Yüze", "Telefon", "Referans", "Diğer"])
                    
                    ustalar_listesi = df_ustalar['ad_soyad'].tolist() if not df_ustalar.empty else ["Usta Atanmadı"]
                    usta_adi = st.selectbox("Atanan Usta", ustalar_listesi)
                    
                    st.markdown("##### 📐 İçerik Sayıları")
                    kolon_sayisi = st.number_input("Kolon Sayısı", min_value=0, step=1, value=0)
                    ic_tesisat_sayisi = st.number_input("İç Tesisat Sayısı", min_value=0, step=1, value=0)
                    diger_islemler = st.multiselect("Diğer İşlemler", ["Sızdırmazlık Testi", "Proje Revizyonu", "Kombi Montajı", "Radyatör Montajı", "Gaz Açımı"])
                    
                    armadas_surec_adimi = st.selectbox("Armadaş Süreç Adımı", [
                        "Proje Çizim Aşamasında",
                        "Armadaş Onayı Bekliyor",
                        "Proje Onaylandı",
                        "Randevu Alındı",
                        "Gaz Açıldı",
                        "Eksik / Red Aldı"
                    ])
                    eksik_red_nedeni = st.text_input("Eksik / Red Nedeni (Varsa)")

                with col_f2:
                    st.markdown("##### 💰 Finansal Durum")
                    toplam_bedel = st.number_input("Proje Toplam Bedeli (TL)", min_value=0.0, step=500.0, value=0.0)
                    alinan_tutar = st.number_input("Alınan Kapora / Ödeme (TL)", min_value=0.0, step=500.0, value=0.0)
                    kalan_tutar_hesaplanan = max(0.0, toplam_bedel - alinan_tutar)
                    st.info(f"**Kalan Bakiye:** ₺{kalan_tutar_hesaplanan:,.2f}")
                    odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet"])

                with col_f3:
                    st.markdown("##### 📦 Malzeme & Sayaç Detayları")
                    sayac_seri_no = st.text_input("Doğalgaz Sayaç Seri No")
                    regulator_durumu = st.selectbox("Regülatör Durumu", ["Gerekmiyor", "Gerekli / Takılacak", "Takıldı"])

                st.markdown("---")
                btn_kaydet = st.form_submit_button("💾 Kaydı Tamamla")
                
                if btn_kaydet:
                    if musteri_adi.strip():
                        seri_no = f"GZ-{datetime.now().year}-{toplam_kayit + 1:03d}"
                        durum = "Tamamlandı" if kalan_tutar_hesaplanan == 0 and toplam_bedel > 0 else ("Kısmi Ödeme" if alinan_tutar > 0 else "Bekliyor")
                        diger_islemler_str = ", ".join(diger_islemler) if diger_islemler else ""
                        
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO kayitlar (
                                seri_no, musteri_adi, telefon, adres, proje_tarihi, proje_gelis_yolu, 
                                usta_adi, kolon_sayisi, ic_tesisat_sayisi, diger_islemler, 
                                armadas_surec_adimi, eksik_red_nedeni, toplam_bedel, alinan_tutar, 
                                kalan_tutar, odeme_yontemi, sayac_seri_no, regulator_durumu, durum
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            seri_no, musteri_adi.strip(), telefon, adres, str(proje_tarihi), proje_gelis_yolu,
                            usta_adi, kolon_sayisi, ic_tesisat_sayisi, diger_islemler_str,
                            armadas_surec_adimi, eksik_red_nedeni, toplam_bedel, alinan_tutar,
                            kalan_tutar_hesaplanan, odeme_yontemi, sayac_seri_no, regulator_durumu, durum
                        ))
                        conn.commit()
                        st.success(f"'{musteri_adi}' projesi eklendi! ({seri_no})")
                        st.session_state['form_acik'] = False
                        st.rerun()
                    else:
                        st.error("Lütfen Müşteri / Proje Adı alanını doldurun.")

    # TABLO
    st.subheader("Son Projeler")
    if not df_kayitlar.empty:
        gosterilecek = [c for c in ['seri_no', 'musteri_adi', 'proje_gelis_yolu', 'usta_adi', 'kolon_sayisi', 'ic_tesisat_sayisi', 'armadas_surec_adimi', 'toplam_bedel', 'alinan_tutar', 'kalan_tutar'] if c in df_kayitlar.columns]
        st.dataframe(
            df_kayitlar[gosterilecek],
            use_container_width=True,
            hide_index=True,
            column_config={
                "seri_no": "Kod",
                "musteri_adi": "Müşteri / Proje",
                "proje_gelis_yolu": "Geliş Yolu",
                "usta_adi": "Usta",
                "kolon_sayisi": "Kolon",
                "ic_tesisat_sayisi": "İç Tesisat",
                "armadas_surec_adimi": "Armadaş Süreci",
                "toplam_bedel": st.column_config.NumberColumn("Toplam (₺)", format="₺%.2f"),
                "alinan_tutar": st.column_config.NumberColumn("Alınan (₺)", format="₺%.2f"),
                "kalan_tutar": st.column_config.NumberColumn("Kalan (₺)", format="₺%.2f")
            }
        )
    else:
        st.info("Henüz eklenmiş bir proje kaydı bulunmuyor.")

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("Tüm Kayıtlar")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    c_s1, c_s2 = st.columns([3, 1])
    with c_s1:
        arama = st.text_input("🔍 Proje, Müşteri veya Usta Ara", "")
    with c_s2:
        durum_filtre = st.selectbox("Armadaş Filtresi", ["Hepsi", "Proje Çizim Aşamasında", "Armadaş Onayı Bekliyor", "Proje Onaylandı", "Randevu Alındı", "Gaz Açıldı", "Eksik / Red Aldı"])
        
    if arama and not df_kayitlar.empty:
        df_kayitlar = df_kayitlar[
            df_kayitlar['musteri_adi'].astype(str).str.contains(arama, case=False, na=False) | 
            df_kayitlar['usta_adi'].astype(str).str.contains(arama, case=False, na=False) |
            df_kayitlar['seri_no'].astype(str).str.contains(arama, case=False, na=False)
        ]
    if durum_filtre != "Hepsi" and not df_kayitlar.empty and 'armadas_surec_adimi' in df_kayitlar:
        df_kayitlar = df_kayitlar[df_kayitlar['armadas_surec_adimi'] == durum_filtre]
        
    st.dataframe(df_kayitlar, use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 3: USTALAR (YENİLENDİ - ÇOK DAHA KOMPAKT)
# ==========================================
elif sayfa == "Ustalar":
    st.title("Ustalar Paneli")
    st.caption("Usta ekleme, düzenleme ve usta bazlı iş durumları")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        with st.expander("➕ Yeni Usta Ekle", expanded=False):
            with st.form("yeni_usta_form", clear_on_submit=True):
                y_ad = st.text_input("Usta Adı Soyadı*")
                y_uzmanlik = st.text_input("Uzmanlık / Alanı", "Doğalgaz Tesisatı")
                y_tel = st.text_input("Telefon", "05XX XXX XX XX")
                y_durum = st.selectbox("Durum", ["Aktif", "Pasif"])
                
                btn_u_ekle = st.form_submit_button("Ustayı Kaydet")
                if btn_u_ekle:
                    if y_ad.strip():
                        try:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum) VALUES (?, ?, ?, ?)",
                                           (y_ad.strip(), y_uzmanlik, y_tel, y_durum))
                            conn.commit()
                            st.success(f"'{y_ad}' eklendi!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Bu isimde bir usta zaten var!")
                    else:
                        st.error("Usta Adı boş bırakılamaz.")

    with col_u2:
        with st.expander("✏️ Usta Düzenle / Sil", expanded=False):
            df_u_edit = pd.read_sql_query("SELECT * FROM ustalar", conn)
            if not df_u_edit.empty:
                secili_u_ad = st.selectbox("İşlem Yapılacak Usta", df_u_edit['ad_soyad'].tolist())
                u_row = df_u_edit[df_u_edit['ad_soyad'] == secili_u_ad].iloc[0]
                
                with st.form("duzenle_usta_form"):
                    e_ad = st.text_input("Ad Soyad", value=u_row['ad_soyad'])
                    e_uzmanlik = st.text_input("Uzmanlık", value=u_row['uzmanlik'])
                    e_tel = st.text_input("Telefon", value=u_row['telefon'])
                    e_durum = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if u_row['durum'] == "Aktif" else 1)
                    
                    cb1, cb2 = st.columns(2)
                    with cb1:
                        btn_guncelle = st.form_submit_button("💾 Güncelle")
                    with cb2:
                        btn_sil = st.form_submit_button("🗑️ Sil")
                    
                    if btn_guncelle:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE ustalar SET ad_soyad=?, uzmanlik=?, telefon=?, durum=? WHERE id=?",
                                       (e_ad.strip(), e_uzmanlik, e_tel, e_durum, int(u_row['id'])))
                        cursor.execute("UPDATE kayitlar SET usta_adi=? WHERE usta_adi=?", (e_ad.strip(), secili_u_ad))
                        conn.commit()
                        st.success("Güncellendi!")
                        st.rerun()
                        
                    if btn_sil:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM ustalar WHERE id=?", (int(u_row['id']),))
                        conn.commit()
                        st.warning(f"'{secili_u_ad}' silindi!")
                        st.rerun()
            else:
                st.info("Kayıtlı usta yok.")

    st.markdown("---")
    
    # KOMPAKT USTA KARTLARI (3'lü Grid Yapısı)
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar", conn)
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    if not df_ustalar.empty:
        cols = st.columns(3)
        for idx, usta in df_ustalar.iterrows():
            col = cols[idx % 3]
            u_isleri = df_kayitlar[df_kayitlar['usta_adi'] == usta['ad_soyad']] if not df_kayitlar.empty else pd.DataFrame()
            toplam_is = len(u_isleri)
            alinan = u_isleri['alinan_tutar'].sum() if not u_isleri.empty and 'alinan_tutar' in u_isleri else 0
            kalan = u_isleri['kalan_tutar'].sum() if not u_isleri.empty and 'kalan_tutar' in u_isleri else 0
            
            status_badge = '<span class="badge badge-success">Aktif</span>' if usta['durum'] == 'Aktif' else '<span class="badge badge-danger">Pasif</span>'
            
            with col:
                st.markdown(f"""
                <div class="usta-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:15px; color:#f3f4f6;">{usta['ad_soyad']}</strong>
                        {status_badge}
                    </div>
                    <div style="color:#9ca3af; font-size:12px; margin-top:3px;">🔧 {usta['uzmanlik']} &nbsp;|&nbsp; 📞 {usta['telefon']}</div>
                    <div class="usta-stats">
                        <div><span style="color:#9ca3af;">İş Sayısı:</span> <b>{toplam_is}</b></div>
                        <div><span style="color:#9ca3af;">Alınan:</span> <b style="color:#10b981;">₺{alinan:,.0f}</b></div>
                        <div><span style="color:#9ca3af;">Kalan:</span> <b style="color:#f59e0b;">₺{kalan:,.0f}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if not u_isleri.empty:
                    pdf_bytes = generate_usta_pdf(usta['ad_soyad'], u_isleri)
                    st.download_button(
                        label=f"📄 {usta['ad_soyad']} PDF İndir",
                        data=bytes(pdf_bytes),
                        file_name=f"{usta['ad_soyad']}_rapor.pdf",
                        mime="application/pdf",
                        key=f"pdf_{usta['id']}",
                        use_container_width=True
                    )
    else:
        st.info("Henüz eklenmiş bir usta bulunmuyor.")

# ==========================================
# SAYFA 4: RAPORLAR
# ==========================================
elif sayfa == "Raporlar":
    st.title("Mali & Operasyonel Raporlar")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    if not df_kayitlar.empty:
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.subheader("Ödeme Yöntemine Göre Dağılım")
            if 'odeme_yontemi' in df_kayitlar and 'alinan_tutar' in df_kayitlar:
                odeme_ozet = df_kayitlar.groupby('odeme_yontemi')['alinan_tutar'].sum().reset_index()
                st.bar_chart(odeme_ozet.set_index('odeme_yontemi'))
        
        with col_r2:
            st.subheader("Armadaş Süreç Dağılımı")
            if 'armadas_surec_adimi' in df_kayitlar:
                surec_ozet = df_kayitlar['armadas_surec_adimi'].value_counts()
                st.bar_chart(surec_ozet)
        
        st.markdown("---")
        st.subheader("Excel Formatında Dışa Aktar")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_kayitlar.to_excel(writer, index=False, sheet_name='Proje Kayitlari')
        
        st.download_button(
            label="📊 Tüm Verileri Excel Olarak İndir",
            data=output.getvalue(),
            file_name=f"gunes_dogalgaz_proje_raporu_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Rapor oluşturmak için henüz veri bulunmuyor.")

# ==========================================
# SAYFA 5: AYARLAR
# ==========================================
elif sayfa == "Ayarlar":
    st.title("Sistem Ayarları")
    st.write("Sistem parametrelerini ve veritabanını buradan yönetebilirsiniz.")
    
    if st.button("⚠️ Tüm Proje Kayıtlarını Sıfırla / Temizle"):
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kayitlar")
        conn.commit()
        st.warning("Tüm proje kayıtları sıfırlandı!")
        st.rerun()

conn.close()
