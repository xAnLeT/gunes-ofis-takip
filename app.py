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
                    eksik_red_nedeni TEXT,
                    toplam_bedel REAL DEFAULT 0.0,
                    alinan_tutar REAL DEFAULT 0.0,
                    kalan_tutar REAL DEFAULT 0.0,
                    odeme_yontemi TEXT,
                    sayac_seri_no TEXT,
                    regulator_durumu TEXT,
                    durum TEXT
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS ustalar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_soyad TEXT UNIQUE,
                    uzmanlik TEXT,
                    telefon TEXT,
                    durum TEXT
                )''')
    
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

# --- GÖRSELDEKİ BİREBİR KOYU TEMA & KART TASARIMLARI (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Ana Arka Plan (Koyu Gece Mavisi) */
    .stApp {
        background-color: #0b101d;
        color: #f3f4f6;
    }
    
    /* Sol Sidebar (Görsel 1 Birebir Mimari) */
    [data-testid="stSidebar"] {
        background-color: #0d1424;
        border-right: 1px solid #1a233a;
        padding-top: 10px;
    }
    
    /* Sidebar Üst Logo Alanı */
    .brand-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 25px;
        padding: 5px 10px;
    }
    .brand-icon {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        width: 42px;
        height: 42px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }
    .brand-title {
        font-weight: 700;
        font-size: 16px;
        color: #ffffff;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 11px;
        color: #64748b;
    }

    /* Görsel 2: Dashboard Kart Tasarımları */
    .dashboard-card {
        background-color: #131c2e;
        border: 1px solid #1e2a45;
        border-radius: 14px;
        padding: 20px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .card-icon-box {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 16px;
    }
    
    /* İkon Arka Plan Renkleri (Görsel 2) */
    .icon-blue { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; }
    .icon-green { background-color: rgba(16, 185, 129, 0.15); color: #34d399; }
    .icon-yellow { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .icon-purple { background-color: rgba(168, 85, 247, 0.15); color: #c084fc; }

    .card-value {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.5px;
        margin-bottom: 4px;
    }
    .card-label {
        font-size: 13px;
        color: #94a3b8;
        font-weight: 500;
        margin-bottom: 6px;
    }
    .card-subtext {
        font-size: 12px;
        font-weight: 600;
    }
    
    .sub-blue { color: #38bdf8; }
    .sub-green { color: #34d399; }
    .sub-yellow { color: #fbbf24; }
    .sub-purple { color: #c084fc; }

    /* Sidebar Alt Profil Alanı (Görsel 1) */
    .sidebar-user-box {
        margin-top: 40px;
        padding: 12px;
        background-color: #131c2e;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
        border: 1px solid #1e2a45;
    }
    .user-avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background-color: #1e293b;
        color: #f59e0b;
        font-weight: 700;
        font-size: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #f59e0b;
    }
    .user-info-name {
        font-size: 13px;
        font-weight: 600;
        color: #ffffff;
    }
    .user-info-email {
        font-size: 11px;
        color: #64748b;
    }

    /* Custom Input & Button Styling */
    .stButton>button {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: #000;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
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

# --- SOL MENÜ (SIDEBAR - Görsel 1 Birebir) ---
with st.sidebar:
    # Üst Logo ve Başlık
    st.markdown("""
    <div class="brand-container">
        <div class="brand-icon">🔥</div>
        <div>
            <div class="brand-title">Güneş Doğalgaz</div>
            <div class="brand-subtitle">Servis Yönetim Sistemi</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigasyon Menüsü
    sayfa = st.radio(
        "",
        ["Dashboard", "Kayıtlar", "Ustalar", "Raporlar", "Ayarlar"],
        label_visibility="collapsed"
    )
    
    # Alt Kullanıcı Profil Kartı
    st.markdown("""
    <div class="sidebar-user-box">
        <div class="user-avatar">YÖ</div>
        <div>
            <div class="user-info-name">Yönetici</div>
            <div class="user-info-email">admin@gunesdogalgaz.com</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

conn = get_db()

# ==========================================
# SAYFA 1: DASHBOARD (Görsel 2 Birebir Kartlar)
# ==========================================
if sayfa == "Dashboard":
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title("Dashboard")
        st.caption("Genel durum özetleri ve finansal göstergeler")
    with col_head2:
        st.write("")
        yeni_kayit_modal = st.button("➕ Yeni Proje Kaydı", use_container_width=True)

    # Verileri Çek
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar WHERE durum='Aktif'", conn)
    
    toplam_kayit = len(df_kayitlar)
    toplam_alinan = df_kayitlar['alinan_tutar'].sum() if not df_kayitlar.empty else 0
    toplam_kalan = df_kayitlar['kalan_tutar'].sum() if not df_kayitlar.empty else 0
    bekleyen_kayit_sayisi = len(df_kayitlar[df_kayitlar['kalan_tutar'] > 0]) if not df_kayitlar.empty else 0
    aktif_usta = len(df_ustalar)

    # GÖRSEL 2: 4'LÜ METRİK KARTLARI DÜZENİ
    c1, c2, c3, c4 = st.columns(4)
    
    # 1. Toplam Kayıt Kartı
    with c1:
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="card-icon-box icon-blue">📋</div>
            <div>
                <div class="card-value">{toplam_kayit}</div>
                <div class="card-label">Toplam Kayıt</div>
                <div class="card-subtext sub-blue">+12 bu ay</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # 2. Bu Ay Alınan (Fiyat) Kartı
    with c2:
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="card-icon-box icon-green">📈</div>
            <div>
                <div class="card-value">₺{toplam_alinan:,.0f}</div>
                <div class="card-label">Bu Ay Alınan</div>
                <div class="card-subtext sub-green">+%18 geçen aya göre</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # 3. Bekleyen Ödeme (Fiyat) Kartı
    with c3:
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="card-icon-box icon-yellow">🕒</div>
            <div>
                <div class="card-value">₺{toplam_kalan:,.0f}</div>
                <div class="card-label">Bekleyen Ödeme</div>
                <div class="card-subtext sub-yellow">{bekleyen_kayit_sayisi} kayıtta bekliyor</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # 4. Aktif Usta Kartı
    with c4:
        st.markdown(f"""
        <div class="dashboard-card">
            <div class="card-icon-box icon-purple">👥</div>
            <div>
                <div class="card-value">{aktif_usta}</div>
                <div class="card-label">Aktif Usta</div>
                <div class="card-subtext sub-purple">{aktif_usta} sahada aktif</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # DÜZENLENEBİLİR FORM ALANI
    if yeni_kayit_modal or st.session_state.get('form_acik', False):
        st.session_state['form_acik'] = True
        with st.expander("📝 Yeni Proje & Fiyat Kaydı Ekle", expanded=True):
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

                with col_f2:
                    st.markdown("##### 💰 Fiyat & Ödeme Düzenleme")
                    toplam_bedel = st.number_input("Toplam Proje Bedeli (TL)*", min_value=0.0, step=500.0, value=0.0)
                    alinan_tutar = st.number_input("Alınan Ödeme / Kapora (TL)", min_value=0.0, step=500.0, value=0.0)
                    kalan_tutar_hesaplanan = max(0.0, toplam_bedel - alinan_tutar)
                    st.info(f"**Hesaplanan Kalan Tutar:** ₺{kalan_tutar_hesaplanan:,.2f}")
                    odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet"])

                with col_f3:
                    st.markdown("##### 📐 Proje & Tesisat Detayları")
                    kolon_sayisi = st.number_input("Kolon Sayısı", min_value=0, step=1, value=0)
                    ic_tesisat_sayisi = st.number_input("İç Tesisat Sayısı", min_value=0, step=1, value=0)
                    armadas_surec_adimi = st.selectbox("Armadaş Süreç Adımı", [
                        "Proje Çizim Aşamasında", "Armadaş Onayı Bekliyor", "Proje Onaylandı", 
                        "Randevu Alındı", "Gaz Açıldı", "Eksik / Red Aldı"
                    ])
                    sayac_seri_no = st.text_input("Sayaç Seri No")

                st.markdown("---")
                btn_kaydet = st.form_submit_button("💾 Kaydet ve Güncelle")
                
                if btn_kaydet:
                    if musteri_adi.strip():
                        seri_no = f"GZ-{datetime.now().year}-{toplam_kayit + 1:03d}"
                        durum = "Tamamlandı" if kalan_tutar_hesaplanan == 0 and toplam_bedel > 0 else ("Kısmi Ödeme" if alinan_tutar > 0 else "Bekliyor")
                        
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO kayitlar (
                                seri_no, musteri_adi, telefon, adres, proje_tarihi, proje_gelis_yolu, 
                                usta_adi, kolon_sayisi, ic_tesisat_sayisi, armadas_surec_adimi, 
                                toplam_bedel, alinan_tutar, kalan_tutar, odeme_yontemi, sayac_seri_no, durum
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            seri_no, musteri_adi.strip(), telefon, adres, str(proje_tarihi), proje_gelis_yolu,
                            usta_adi, kolon_sayisi, ic_tesisat_sayisi, armadas_surec_adimi,
                            toplam_bedel, alinan_tutar, kalan_tutar_hesaplanan, odeme_yontemi, sayac_seri_no, durum
                        ))
                        conn.commit()
                        st.success(f"'{musteri_adi}' kaydedildi! ({seri_no})")
                        st.session_state['form_acik'] = False
                        st.rerun()
                    else:
                        st.error("Lütfen Müşteri Adı alanını doldurun.")

    # SON PROJELER VE FİYAT TABLOSU
    st.subheader("Son Eklenen Projeler")
    if not df_kayitlar.empty:
        gosterilecek = ['seri_no', 'musteri_adi', 'usta_adi', 'armadas_surec_adimi', 'toplam_bedel', 'alinan_tutar', 'kalan_tutar']
        st.dataframe(
            df_kayitlar[gosterilecek],
            use_container_width=True,
            hide_index=True,
            column_config={
                "seri_no": "Kod",
                "musteri_adi": "Müşteri / Proje",
                "usta_adi": "Usta",
                "armadas_surec_adimi": "Armadaş Süreci",
                "toplam_bedel": st.column_config.NumberColumn("Toplam Bedel (₺)", format="₺%.2f"),
                "alinan_tutar": st.column_config.NumberColumn("Alınan Ödeme (₺)", format="₺%.2f"),
                "kalan_tutar": st.column_config.NumberColumn("Kalan Bakiye (₺)", format="₺%.2f")
            }
        )
    else:
        st.info("Henüz eklenmiş proje kaydı yok.")

# ==========================================
# SAYFA 2: KAYITLAR
# ==========================================
elif sayfa == "Kayıtlar":
    st.title("Tüm Kayıtlar & Filtreleme")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar ORDER BY id DESC", conn)
    
    arama = st.text_input("🔍 Proje, Müşteri veya Usta Ara", "")
    if arama and not df_kayitlar.empty:
        df_kayitlar = df_kayitlar[
            df_kayitlar['musteri_adi'].astype(str).str.contains(arama, case=False, na=False) | 
            df_kayitlar['usta_adi'].astype(str).str.contains(arama, case=False, na=False) |
            df_kayitlar['seri_no'].astype(str).str.contains(arama, case=False, na=False)
        ]
        
    st.dataframe(df_kayitlar, use_container_width=True, hide_index=True)

# ==========================================
# SAYFA 3: USTALAR
# ==========================================
elif sayfa == "Ustalar":
    st.title("Ustalar Yönetim Paneli")
    
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

    df_ustalar = pd.read_sql_query("SELECT * FROM ustalar", conn)
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    if not df_ustalar.empty:
        cols = st.columns(3)
        for idx, usta in df_ustalar.iterrows():
            col = cols[idx % 3]
            u_isleri = df_kayitlar[df_kayitlar['usta_adi'] == usta['ad_soyad']] if not df_kayitlar.empty else pd.DataFrame()
            toplam_is = len(u_isleri)
            alinan = u_isleri['alinan_tutar'].sum() if not u_isleri.empty else 0
            kalan = u_isleri['kalan_tutar'].sum() if not u_isleri.empty else 0
            
            with col:
                st.markdown(f"""
                <div style="background-color:#131c2e; border:1px solid #1e2a45; border-radius:10px; padding:15px; margin-bottom:15px;">
                    <strong style="font-size:16px; color:#fff;">{usta['ad_soyad']}</strong>
                    <div style="color:#94a3b8; font-size:12px; margin-top:4px;">🔧 {usta['uzmanlik']} | 📞 {usta['telefon']}</div>
                    <div style="display:flex; justify-content:space-between; background-color:#0d1424; padding:8px; border-radius:6px; margin-top:10px; font-size:12px;">
                        <span>İş: <b>{toplam_is}</b></span>
                        <span style="color:#34d399;">Alınan: <b>₺{alinan:,.0f}</b></span>
                        <span style="color:#fbbf24;">Kalan: <b>₺{kalan:,.0f}</b></span>
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

# ==========================================
# SAYFA 4: RAPORLAR
# ==========================================
elif sayfa == "Raporlar":
    st.title("Mali Raporlar & Dışa Aktar")
    df_kayitlar = pd.read_sql_query("SELECT * FROM kayitlar", conn)
    
    if not df_kayitlar.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_kayitlar.to_excel(writer, index=False, sheet_name='Proje Kayitlari')
        
        st.download_button(
            label="📊 Excel Raporu İndir",
            data=output.getvalue(),
            file_name=f"gunes_dogalgaz_rapor_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Raporlanacak veri bulunmuyor.")

# ==========================================
# SAYFA 5: AYARLAR
# ==========================================
elif sayfa == "Ayarlar":
    st.title("Sistem Ayarları")
    if st.button("⚠️ Tüm Kayıtları Temizle"):
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kayitlar")
        conn.commit()
        st.warning("Veriler sıfırlandı!")
        st.rerun()

conn.close()
