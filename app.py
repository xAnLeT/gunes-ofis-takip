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
                    usta_adi TEXT,
                    proje_tarihi TEXT,
                    dogalgaz_seri_no TEXT,
                    is_aciklamasi TEXT,
                    alinan_tutar REAL,
                    kalan_tutar REAL,
                    odeme_yontemi TEXT,
                    fatura_no TEXT,
                    durum TEXT
                )''')
    # Ustalar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS ustalar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_soyad TEXT UNIQUE,
                    uzmanlik TEXT,
                    telefon TEXT,
                    durum TEXT
                )''')
    
    # Varsayılan Ustaları Ekle (Yoksa)
    varsayilan_ustalar = [
        ("Mehmet Usta", "Doğalgaz Tesisatı", "0532 111 2233", "Aktif"),
        ("Ali Usta", "Kombi & Kazan", "0533 222 3344", "Aktif"),
        ("Hüseyin Usta", "Doğalgaz Tesisatı", "0534 333 4455", "Aktif"),
        ("Kadir Usta", "Boru Döşeme", "0535 444 5566", "Aktif"),
        ("Serkan Usta", "Kombi Bakım", "0536 555 6677", "Pasif"),
        ("Emre Usta", "Doğalgaz Tesisatı", "0537 666 7788", "Aktif")
    ]
    for usta in varsayilan_ustalar:
        try:
            c.execute("INSERT INTO ustalar (ad_soyad, uzmanlik, telefon, durum) VALUES (?, ?, ?, ?)", usta)
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()

init_db()

# --- ÖZEL KOYU TEMA (CSS) ---
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    
    /* Sol Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Kart Yapıları */
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    /* Metin Renkleri */
    .metric-title { color: #8b949e; font-size: 13px; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 28px; font-weight: bold; margin: 5px 0; }
    .metric-sub { font-size: 12px; }
    .text-green { color: #3fb950; }
    .text-yellow { color: #d29922; }
    .text-blue { color: #58a6ff; }
    
    /* Durum Rozetleri */
    .badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-success { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid rgba(63, 185, 80, 0.4); }
    .badge-warning { background-color: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid rgba(210, 153, 34, 0.4); }
    .badge-danger { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid rgba(248, 81, 73, 0.4); }

    /* Buton Tasarımları */
    .stButton>button {
        background-color: #f59e0b;
        color: #000000;
        font-weight: bold;
        border-radius: 6px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #d97706;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# --- PDF OLUŞTURUCU ---
def generate_usta_pdf(usta_adi, df_usta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(190, 10, f"Gunes Dogalgaz - Usta Raporu: {usta_adi}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, 8, "Tarih", 1)
    pdf.cell(50, 8, "Musteri", 1)
    pdf.cell(40, 8, "Alinan (TL)", 1)
    pdf.cell(40, 8, "Kalan (TL)", 1)
    pdf.cell(30, 8, "Durum", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", '', 9)
    for _, row in df_usta.iterrows():
        pdf.cell(30, 8, str(row['proje_tarihi']), 1)
        pdf.cell(50, 8, str(row['musteri_adi'])[:20], 1)
        pdf.cell(40, 8, f"{row['alinan_tutar']:,.2f}", 1)
        pdf.cell(40, 8, f"{row['kalan_tutar']:,.2f}", 1)
        pdf.cell(30, 8, str(row['durum']), 1)
        pdf.ln()
        
    return pdf.output()

# --- SOL MENÜ (SIDEBAR) ---
with st.sidebar:
    st.markdown("### 🔥 Güneş Doğalgaz")
    st.caption("Servis Yönetim Sistemi")
    st.markdown("---")
    
    sayfa = st.radio(
        "MENÜ",
        ["Dashboard", "Kayıtlar", "Ustalar", "Raporlar", "Ayarlar"],
        icon="📌"
    )
    
    st.markdown("---")
    st.markdown("👤 **Yönetici**")
    st.caption("admin@gunesdogalgaz.com")

conn = get_db()

# ==========================================
# SAYFA 1: DASHBOARD
# ==========================================
if sayfa == "Dashboard":
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title("Dashboard")
        st.caption(f"Özet Göstergeler ve Son İşlemler ({datetime.now().strftime('%B %Y')})")
    with col_head2:
        st.write("")
        yeni_kayit_modal = st.button("➕ Yeni Kayıt Ekle", use_container_width=True)

    # İstatistik Hesaplamaları
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar WHERE durum='Aktif'", conn)
    
    toplam_kayit = len(df_kayitlar)
    toplam_alinan = df_kayitlar['alinan_tutar'].sum() if not df_kayitlar.empty else 0
    toplam_kalan = df_kayitlar['kalan_tutar'].sum() if not df_kayitlar.empty else 0
    aktif_usta = len(df_ustalar)

    # 4'lü Üst Kart Yapısı
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TOPLAM KAYIT</div>
            <div class="metric-value">{toplam_kayit}</div>
            <div class="metric-sub text-blue">Sistemde Kayıtlı İş</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">BU AY ALINAN</div>
            <div class="metric-value text-green">₺{toplam_alinan:,.0f}</div>
            <div class="metric-sub text-green">Tahsil Edilen Toplam</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">BEKLEYEN ÖDEME</div>
            <div class="metric-value text-yellow">₺{toplam_kalan:,.0f}</div>
            <div class="metric-sub text-yellow">Kalan Bakiye</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">AKTİF USTA</div>
            <div class="metric-value">{aktif_usta}</div>
            <div class="metric-sub text-blue">Sahada Çalışan</div>
        </div>
        """, unsafe_allow_html=True)

    # Yeni Kayıt Formu
    if yeni_kayit_modal or st.session_state.get('form_acik', False):
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Servis / Proje Kaydı Ekle", expanded=True):
            with st.form("yeni_kayit_formu", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    musteri_adi = st.text_input("Müşteri Adı Soyadı*")
                    telefon = st.text_input("Müşteri Telefonu")
                    adres = st.text_area("Adres / Konum", height=100)
                with col_f2:
                    ustalar_listesi = df_ustalar['ad_soyad'].tolist() if not df_ustalar.empty else ["Usta Bulunamadı"]
                    usta_adi = st.selectbox("Görevli Usta*", ustalar_listesi)
                    proje_tarihi = st.date_input("Proje / Servis Tarihi", datetime.now())
                    dogalgaz_seri_no = st.text_input("Doğalgaz Seri No")
                with col_f3:
                    alinan_tutar = st.number_input("Alınan Tutar (₺)", min_value=0.0, step=100.0)
                    kalan_tutar = st.number_input("Kalan Tutar (₺)", min_value=0.0, step=100.0)
                    odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı"])
                    fatura_no = st.text_input("Fatura / Makbuz No")

                is_aciklamasi = st.text_input("İş Açıklaması / Notlar")
                
                btn_kaydet = st.form_submit_button("Kaydı Tamamla")
                if btn_kaydet:
                    if musteri_adi:
                        seri_no = f"GZ-{datetime.now().year}-{toplam_kayit + 1:03d}"
                        durum = "Tamamlandı" if kalan_tutar == 0 else ("Kısmi Ödeme" if alinan_tutar > 0 else "Bekliyor")
                        
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO kayitlar (seri_no, musteri_adi, telefon, adres, usta_adi, proje_tarihi, dogalgaz_seri_no, is_aciklamasi, alinan_tutar, kalan_tutar, odeme_yontemi, fatura_no, durum)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (seri_no, musteri_adi, telefon, adres, usta_adi, str(proje_tarihi), dogalgaz_seri_no, is_aciklamasi, alinan_tutar, kalan_tutar, odeme_yontemi, fatura_no, durum))
                        conn.commit()
                        st.success(f"{musteri_adi} kaydı başarıyla oluşturuldu! ({seri_no})")
                        st.session_state['form_acik'] = False
                        st.rerun()
                    else:
                        st.error("Lütfen Müşteri Adı alanını doldurun.")

    # Tablo Listesi
    st.subheader("Son Kayıtlar")
    if not df_kayitlar.empty:
        st.dataframe(
            df_kayitlar[['seri_no', 'musteri_adi', 'usta_adi', 'proje_tarihi', 'alinan_tutar', 'kalan_tutar', 'odeme_yontemi', 'durum']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "seri_no": "Kod",
                "musteri_adi": "Müşteri Adı",
                "usta_adi": "Usta",
                "proje_tarihi": "Tarih",
                "alinan_tutar": st.column_config.NumberColumn("Alınan Tutar", format="₺%.2f"),
                "kalan_tutar": st.column_config.NumberColumn("Kalan Tutar", format="₺%.2f"),
                "odeme_yontemi": "Ödeme Tipi",
                "durum": "Durum"
            }
        )
    else:
        st.info("Henüz eklenmiş bir servis kaydı bulunmuyor.")

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("Tüm Servis Kayıtları")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        arama = st.text_input("🔍 Müşteri, Usta veya Kod Arama", "")
    with col_search2:
        durum_filtre = st.selectbox("Durum Filtresi", ["Hepsi", "Tamamlandı", "Kısmi Ödeme", "Bekliyor"])
        
    if arama:
        df_kayitlar = df_kayitlar[df_kayitlar['musteri_adi'].str.contains(arama, case=False, na=False) | 
                                 df_kayitlar['usta_adi'].str.contains(arama, case=False, na=False) |
                                 df_kayitlar['seri_no'].str.contains(arama, case=False, na=False)]
    if durum_filtre != "Hepsi":
        df_kayitlar = df_kayitlar[df_kayitlar['durum'] == durum_filtre]
        
    st.dataframe(df_kayitlar, use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 3: USTALAR
# ==========================================
elif sayfa == "Ustalar":
    st.title("Ustalar ve Performans Özeti")
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar", conn)
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    # 3'lü Grid Kart Mimarisi
    cols = st.columns(3)
    for idx, usta in df_ustalar.iterrows():
        col = cols[idx % 3]
        u_isleri = df_kayitlar[df_kayitlar['usta_adi'] == usta['ad_soyad']]
        toplam_is = len(u_isleri)
        alinan = u_isleri['alinan_tutar'].sum() if not u_isleri.empty else 0
        kalan = u_isleri['kalan_tutar'].sum() if not u_isleri.empty else 0
        
        tamamlanan = len(u_isleri[u_isleri['durum'] == 'Tamamlandı'])
        bekleyen = len(u_isleri[u_isleri['durum'] != 'Tamamlandı'])
        
        status_badge = '<span class="badge badge-success">Aktif</span>' if usta['durum'] == 'Aktif' else '<span class="badge badge-danger">Pasif</span>'
        
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div style="display:flex; justify-between; align-items:center;">
                    <h3 style="margin:0; color:#58a6ff;">{usta['ad_soyad']}</h3>
                    <div>{status_badge}</div>
                </div>
                <p style="color:#8b949e; font-size:12px; margin-bottom:10px;">🔧 {usta['uzmanlik']} | 📞 {usta['telefon']}</p>
                <hr style="border-color:#30363d;">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <div class="metric-title">TOPLAM İŞ</div>
                        <div style="font-size:18px; font-weight:bold;">{toplam_is}</div>
                        <div style="font-size:11px; color:#3fb950;">{tamamlanan} tamamlandı</div>
                    </div>
                    <div>
                        <div class="metric-title">ALINAN TUTAR</div>
                        <div style="font-size:18px; font-weight:bold; color:#3fb950;">₺{alinan:,.0f}</div>
                        <div style="font-size:11px; color:#d29922;">₺{kalan:,.0f} kalan</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # PDF Raporlama Butonu
            if not u_isleri.empty:
                pdf_bytes = generate_usta_pdf(usta['ad_soyad'], u_isleri)
                st.download_button(
                    label=f"📄 {usta['ad_soyad']} PDF Raporu İndir",
                    data=bytes(pdf_bytes),
                    file_name=f"{usta['ad_soyad']}_rapor.pdf",
                    mime="application/pdf",
                    key=f"pdf_{usta['id']}"
                )

# ==========================================
# SAYFA 4: RAPORLAR
# ==========================================
elif sayfa == "Raporlar":
    st.title("Mali & Operasyonel Raporlar")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    if not df_kayitlar.empty:
        st.subheader("Ödeme Yöntemine Göre Dağılım")
        odeme_ozet = df_kayitlar.groupby('odeme_yontemi')['alinan_tutar'].sum().reset_index()
        st.bar_chart(odeme_ozet.set_index('odeme_yontemi'))
        
        st.subheader("Excel Formatında Dışa Aktar")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_kayitlar.to_excel(writer, index=False, sheet_name='Servis Kayitlari')
        
        st.download_button(
            label="📊 Tüm Verileri Excel Olarak İndir",
            data=output.getvalue(),
            file_name=f"gunes_dogalgaz_rapor_{datetime.now().strftime('%Y%m%d')}.xlsx",
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
    
    if st.button("⚠️ Veritabanını Sıfırla / Temizle"):
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kayitlar")
        conn.commit()
        st.warning("Tüm servis kayıtları sıfırlandı!")
        st.rerun()

conn.close()
