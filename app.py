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
    
    # Kayıtlar Tablosu (Gelişmiş Alanlar İle)
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
                
    # Var olan veritabanında eksik sütunlar varsa otomatik ekle (Migration)
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
    
    # Varsayılan Ustaları Ekle (İlk kurulum için)
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
    st.caption("Servis & Proje Yönetim Sistemi")
    st.markdown("---")
    
    sayfa = st.radio(
        "📌 MENÜ",
        ["Dashboard", "Kayıtlar", "Ustalar", "Raporlar", "Ayarlar"]
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
        st.caption(f"Özet Göstergeler ve Proje Takibi ({datetime.now().strftime('%B %Y')})")
    with col_head2:
        st.write("")
        yeni_kayit_modal = st.button("➕ Yeni Proje / Kayıt Ekle", use_container_width=True)

    # İstatistik Hesaplamaları
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar WHERE durum='Aktif'", conn)
    
    toplam_kayit = len(df_kayitlar)
    toplam_toplam_bedel = df_kayitlar['toplam_bedel'].sum() if not df_kayitlar.empty and 'toplam_bedel' in df_kayitlar else 0
    toplam_alinan = df_kayitlar['alinan_tutar'].sum() if not df_kayitlar.empty else 0
    toplam_kalan = df_kayitlar['kalan_tutar'].sum() if not df_kayitlar.empty else 0
    aktif_usta = len(df_ustalar)

    # 4'lü Üst Kart Yapısı
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TOPLAM PROJE</div>
            <div class="metric-value">{toplam_kayit}</div>
            <div class="metric-sub text-blue">Sistemdeki İş Sayısı</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TAHSİL EDİLEN</div>
            <div class="metric-value text-green">₺{toplam_alinan:,.0f}</div>
            <div class="metric-sub text-green">Alınan Toplam Kapora</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">BEKLEYEN ALACAK</div>
            <div class="metric-value text-yellow">₺{toplam_kalan:,.0f}</div>
            <div class="metric-sub text-yellow">Kalan Bakiye</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">AKTİF USTA</div>
            <div class="metric-value">{aktif_usta}</div>
            <div class="metric-sub text-blue">Sahada Çalışan Usta</div>
        </div>
        """, unsafe_allow_html=True)

    # GÖRSELDEKİ BİREBİR FORM YAPISI
    if yeni_kayit_modal or st.session_state.get('form_acik', False):
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Proje Kaydı Ekle", expanded=True):
            with st.form("yeni_kayit_formu", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                
                # --- 1. SÜTUN: Genel Bilgiler & İçerik Sayıları ---
                with col_f1:
                    st.markdown("##### 📌 Genel Bilgiler")
                    proje_tarihi = st.date_input("Proje / Kayıt Tarihi", datetime.now())
                    musteri_adi = st.text_input("Müşteri / Proje Adı*")
                    telefon = st.text_input("Müşteri Telefonu")
                    adres = st.text_area("Adres / Açıklama", height=68)
                    proje_gelis_yolu = st.selectbox("Proje Geliş Yolu", ["WhatsApp", "Ofis / Yüz Yüze", "Telefon", "Referans", "Diğer"])
                    
                    ustalar_listesi = df_ustalar['ad_soyad'].tolist() if not df_ustalar.empty else ["Usta Atanmadı"]
                    usta_adi = st.selectbox("Atanan Usta", ustalar_listesi)
                    
                    st.markdown("##### 📐 Proje İçerik Sayıları")
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

                # --- 2. SÜTUN: Finansal Durum ---
                with col_f2:
                    st.markdown("##### 💰 Finansal Durum")
                    toplam_bedel = st.number_input("Proje Toplam Bedeli (TL)", min_value=0.0, step=500.0, value=0.0)
                    alinan_tutar = st.number_input("Alınan Kapora / Ödeme (TL)", min_value=0.0, step=500.0, value=0.0)
                    kalan_tutar_hesaplanan = max(0.0, toplam_bedel - alinan_tutar)
                    st.info(f"**Kalan Bakiye:** ₺{kalan_tutar_hesaplanan:,.2f}")
                    odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet"])

                # --- 3. SÜTUN: Malzeme & Sayaç Detayları ---
                with col_f3:
                    st.markdown("##### 📦 Malzeme & Sayaç Detayları")
                    sayac_seri_no = st.text_input("Doğalgaz Sayaç Seri No")
                    regulator_durumu = st.selectbox("Regülatör Durumu", ["Gerekmiyor", "Gerekli / Takılacak", "Takıldı"])

                st.markdown("---")
                btn_kaydet = st.form_submit_button("💾 Kaydı Tamamla ve Oluştur")
                
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
                        st.success(f"'{musteri_adi}' projesi başarıyla kaydedildi! ({seri_no})")
                        st.session_state['form_acik'] = False
                        st.rerun()
                    else:
                        st.error("Lütfen Müşteri / Proje Adı alanını doldurun.")

    # Tablo Listesi
    st.subheader("Son Projeler ve Servis Kayıtları")
    if not df_kayitlar.empty:
        gosterilecek_kolonlar = [c for c in ['seri_no', 'musteri_adi', 'proje_gelis_yolu', 'usta_adi', 'kolon_sayisi', 'ic_tesisat_sayisi', 'armadas_surec_adimi', 'toplam_bedel', 'alinan_tutar', 'kalan_tutar', 'durum'] if c in df_kayitlar.columns]
        st.dataframe(
            df_kayitlar[gosterilecek_kolonlar],
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
                "kalan_tutar": st.column_config.NumberColumn("Kalan (₺)", format="₺%.2f"),
                "durum": "Durum"
            }
        )
    else:
        st.info("Henüz eklenmiş bir proje kaydı bulunmuyor.")

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("Tüm Proje & Servis Kayıtları")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        arama = st.text_input("🔍 Müşteri, Usta, Seri No veya Süreç Arama", "")
    with col_search2:
        durum_filtre = st.selectbox("Armadaş Süreç Filtresi", ["Hepsi", "Proje Çizim Aşamasında", "Armadaş Onayı Bekliyor", "Proje Onaylandı", "Randevu Alındı", "Gaz Açıldı", "Eksik / Red Aldı"])
        
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
# SAYFA 3: USTALAR
# ==========================================
elif sayfa == "Ustalar":
    st.title("Ustalar Yönetimi & Performans Özetleri")
    
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
                            st.success(f"'{y_ad}' başarıyla eklendi!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Bu isimde bir usta zaten sistemde kayıtlı!")
                    else:
                        st.error("Lütfen Usta Adı Soyadı alanını doldurun.")

    with col_u2:
        with st.expander("✏️ Usta Düzenle veya Sil", expanded=False):
            df_u_edit = pd.read_sql_query("SELECT * FROM ustalar", conn)
            if not df_u_edit.empty:
                secili_u_ad = st.selectbox("İşlem Yapılacak Usta", df_u_edit['ad_soyad'].tolist())
                u_row = df_u_edit[df_u_edit['ad_soyad'] == secili_u_ad].iloc[0]
                
                with st.form("duzenle_usta_form"):
                    e_ad = st.text_input("Ad Soyad", value=u_row['ad_soyad'])
                    e_uzmanlik = st.text_input("Uzmanlık", value=u_row['uzmanlik'])
                    e_tel = st.text_input("Telefon", value=u_row['telefon'])
                    e_durum = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if u_row['durum'] == "Aktif" else 1)
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        btn_guncelle = st.form_submit_button("💾 Bilgileri Güncelle")
                    with col_btn2:
                        btn_sil = st.form_submit_button("🗑️ Ustayı Sil")
                    
                    if btn_guncelle:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE ustalar SET ad_soyad=?, uzmanlik=?, telefon=?, durum=? WHERE id=?",
                                       (e_ad.strip(), e_uzmanlik, e_tel, e_durum, int(u_row['id'])))
                        cursor.execute("UPDATE kayitlar SET usta_adi=? WHERE usta_adi=?", (e_ad.strip(), secili_u_ad))
                        conn.commit()
                        st.success("Usta bilgileri güncellendi!")
                        st.rerun()
                        
                    if btn_sil:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM ustalar WHERE id=?", (int(u_row['id']),))
                        conn.commit()
                        st.warning(f"'{secili_u_ad}' sistemden silindi!")
                        st.rerun()
            else:
                st.info("Sistemde düzenlenecek usta bulunamadı.")

    st.markdown("---")
    
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
            
            tamamlanan = len(u_isleri[u_isleri['durum'] == 'Tamamlandı']) if not u_isleri.empty and 'durum' in u_isleri else 0
            status_badge = '<span class="badge badge-success">Aktif</span>' if usta['durum'] == 'Aktif' else '<span class="badge badge-danger">Pasif</span>'
            
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
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
                
                if not u_isleri.empty:
                    pdf_bytes = generate_usta_pdf(usta['ad_soyad'], u_isleri)
                    st.download_button(
                        label=f"📄 {usta['ad_soyad']} PDF Raporu İndir",
                        data=bytes(pdf_bytes),
                        file_name=f"{usta['ad_soyad']}_rapor.pdf",
                        mime="application/pdf",
                        key=f"pdf_{usta['id']}"
                    )
    else:
        st.info("Henüz eklenmiş bir usta yok.")

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
