import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. SİTE VE SAYFA YAPILANDIRMASI
# ==========================================
st.set_page_config(
    page_title="Güneş Doğalgaz & Mühendislik - Ofis Takip Paneli",
    page_icon="🔧",
    layout="wide"
)

# ==========================================
# 2. TV / Mİ STİCK UYUMLULUĞU VE KUMANDA DESTEĞİ
# ==========================================
tv_ui_code = """
<style>
body.is-tv {
    font-size: 24px !important;
    background-color: #0b0f19 !important;
    color: #ffffff !important;
}

body.is-tv button, 
body.is-tv .stButton>button,
body.is-tv input, 
body.is-tv select {
    font-size: 22px !important;
    padding: 15px 30px !important;
    border-radius: 10px !important;
}

body.is-tv *:focus {
    outline: 5px solid #ff9900 !important;
    outline-offset: 4px !important;
    transform: scale(1.05);
    transition: transform 0.2s ease;
}
</style>

<script>
document.addEventListener("DOMContentLoaded", function() {
    const ua = navigator.userAgent.toLowerCase();
    const isTV = ua.includes("android tv") || 
                 ua.includes("smarttv") || 
                 ua.includes("googletv") || 
                 ua.includes("aft") || 
                 window.innerWidth <= 960;

    if (isTV) {
        document.body.classList.add("is-tv");
        console.log("TV / Mi Stick Modu Aktif Edildi.");
    }

    const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    
    document.addEventListener('keydown', function(e) {
        if (!document.body.classList.contains("is-tv")) return;

        const focusable = Array.from(document.querySelectorAll(focusableElements));
        let index = focusable.indexOf(document.activeElement);

        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            index = (index + 1) % focusable.length;
            focusable[index].focus();
        } 
        else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            index = (index - 1 + focusable.length) % focusable.length;
            focusable[index].focus();
        }
    });
});
</script>
"""
st.markdown(tv_ui_code, unsafe_allow_html=True)

# ==========================================
# 3. VERİ YÖNETİMİ (Session State Başlangıcı)
# ==========================================
if "projeler" not in st.session_state:
    st.session_state.projeler = [
        {"Tarih": "2026-06-01", "Proje": "Merkezi Sistem Tesisat", "Müşteri": "Ahmet Yılmaz", "Durum": "Tamamlandı", "Tutar": 45000},
        {"Tarih": "2026-06-05", "Proje": "Kombi Montaj ve Proje", "Müşteri": "Mehmet Demir", "Durum": "Devam Ediyor", "Tutar": 18000}
    ]

# ==========================================
# 4. ANA EKRAN VE BAŞLIK
# ==========================================
st.title("☀️ Güneş Doğalgaz & Mühendislik")
st.subheader("Ofis Proje, Mali ve Usta Performans Takip Paneli (v2)")

# Sekmeler (Tabs)
tab1, tab2, tab3 = st.tabs([
    "🚀 İş / Proje Takibi", 
    "📈 Ofis Detaylı Mali ve Usta Performans Analiz Paneli", 
    "📅 Geçmiş ve Düzenleme"
])

# --- TAB 1: İŞ / PROJE TAKİBİ ---
with tab1:
    st.markdown("### Yeni Proje veya İş Kaydı Ekle")
    
    col1, col2 = st.columns(2)
    with col1:
        proje_adi = st.text_input("Proje / İş Adı")
        musteri_adi = st.text_input("Müşteri Adı Soyadı")
        is_tarihi = st.date_input("İş Tarihi", value=datetime.today())
    
    with col2:
        durum = st.selectbox("İş Durumu", ["Devam Ediyor", "Tamamlandı", "Beklemede"])
        tutar = st.number_input("Proje Bedeli (TL)", min_value=0, step=1000)
    
    if st.button("Kaydı Ekle"):
        if proje_adi and musteri_adi:
            yeni_kayit = {
                "Tarih": str(is_tarihi),
                "Proje": proje_adi,
                "Müşteri": musteri_adi,
                "Durum": durum,
                "Tutar": tutar
            }
            st.session_state.projeler.append(yeni_kayit)
            st.success(f"'{proje_adi}' başarıyla sisteme kaydedildi!")
        else:
            st.warning("Lütfen proje adını ve müşteri bilgisini eksiksiz doldurun.")
            
    st.markdown("---")
    st.markdown("### Mevcut Aktif İşler Listesi")
    if st.session_state.projeler:
        df_projeler = pd.DataFrame(st.session_state.projeler)
        st.dataframe(df_projeler, use_container_width=True)
    else:
        st.info("Henüz kayıtlı bir proje bulunmuyor.")

# --- TAB 2: OFİS DETAYLI MALİ VE USTA PERFORMANS ANALİZ PANELİ ---
with tab2:
    st.markdown("### 📊 Ofis Detaylı Mali ve Usta Performans Analiz Paneli")
    
    st.markdown("Raporlama Periyodu Seçin:")
    rapor_turu = st.radio("", ["Aylık Raporlama", "Haftalık Raporlama"], horizontal=True, label_visibility="collapsed", key="rapor_turu_secimi")
    
    st.markdown("İncelemek İstediğiniz Mali Ayı Seçin:")
    secilen_ay = st.selectbox("", ["2026-06", "2026-05", "2026-04"], label_visibility="collapsed", key="mali_ay_secimi")

    # Usta performans ve detay veri seti
    usta_veri = [
        {
            "Usta Adı": "GÜNEŞ DOĞALGAZ GNS",
            "Toplam İş (Adet)": 1,
            "Kolon Sayısı": 1,
            "İç Tesisat Sayısı": 0,
            "Cihaz Değişimi": 1,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 5000,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "MARTES HİLMİ NOKAY",
            "Toplam İş (Adet)": 3,
            "Kolon Sayısı": 3,
            "İç Tesisat Sayısı": 1,
            "Cihaz Değişimi": 3,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 22000,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "MEHMET BEKİROĞLU",
            "Toplam İş (Adet)": 5,
            "Kolon Sayısı": 5,
            "İç Tesisat Sayısı": 4,
            "Cihaz Değişimi": 5,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 50000,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "MEHMET YİĞİT",
            "Toplam İş (Adet)": 1,
            "Kolon Sayısı": 1,
            "İç Tesisat Sayısı": 0,
            "Cihaz Değişimi": 1,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 3500,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "MUHAMMET SÜT",
            "Toplam İş (Adet)": 1,
            "Kolon Sayısı": 1,
            "İç Tesisat Sayısı": 0,
            "Cihaz Değişimi": 1,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 3500,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "MUSTAFA GÜL",
            "Toplam İş (Adet)": 1,
            "Kolon Sayısı": 1,
            "İç Tesisat Sayısı": 1,
            "Cihaz Değişimi": 1,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 7000,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "SURİYELİ MUHAMMET",
            "Toplam İş (Adet)": 1,
            "Kolon Sayısı": 1,
            "İç Tesisat Sayısı": 1,
            "Cihaz Değişimi": 1,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 7000,
            "Tahsil Edilen (TL)": 0
        },
        {
            "Usta Adı": "VATAN SİNAN",
            "Toplam İş (Adet)": 1,
            "Kolon Sayısı": 1,
            "İç Tesisat Sayısı": 0,
            "Cihaz Değişimi": 1,
            "Randevu Reddi": 0,
            "Ürettiği Toplam Ciro (TL)": 3500,
            "Tahsil Edilen (TL)": 0
        }
    ]

    df_usta = pd.DataFrame(usta_veri)

    # Üst Maliyet Metrik Hesaplamaları
    toplam_ciro = df_usta["Ürettiği Toplam Ciro (TL)"].sum()
    toplam_tahsil_edilen = df_usta["Tahsil Edilen (TL)"].sum()
    kalan_alacak = toplam_ciro - toplam_tahsil_edilen

    # Metrik Kartları
    m1, m2, m3 = st.columns(3)
    m1.metric(label=f"🔥 Toplam Ciro ({secilen_ay})", value=f"{toplam_ciro:,.2f} ₺")
    m2.metric(label="✅ Toplam Tahsil Edilen", value=f"{toplam_tahsil_edilen:,.2f} ₺")
    m3.metric(label="🚨 Kalan Ofis Alacağı", value=f"{kalan_alacak:,.2f} ₺")

    st.markdown("---")
    st.subheader(f"📊 {secilen_ay} Dönemi Usta Detaylı İş/İçerik Dağılım Sayıları")

    # Grafik ve Tablo Yan Yana Yerleşimi
    col_chart, col_table = st.columns([1.3, 1])

    with col_chart:
        st.markdown("##### Ustaların Kolon ve İç Tesisat Yarışı (Grafik)")
        chart_data = df_usta.set_index("Usta Adı")[["Kolon Sayısı", "İç Tesisat Sayısı"]]
        st.bar_chart(chart_data)

    with col_table:
        st.markdown("##### Net Adet Raporlama Tablosu")
        display_df = df_usta[["Usta Adı", "Toplam İş (Adet)", "Kolon Sayısı", "İç Tesisat Sayısı", "Cihaz Değişimi", "Randevu Reddi", "Ürettiği Toplam Ciro (TL)"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- TAB 3: GEÇMİŞ VE DÜZENLEME ---
with tab3:
    st.markdown("### 🕒 Geçmiş Tarihli Kayıtlar ve Yönetim")
    st.write("Buradan geçmiş tarihlere ait projeleri inceleyebilir veya listeden silebilirsiniz.")
    
    if st.session_state.projeler:
        silinecek_index = st.selectbox("Silinecek Projeyi Seçin", options=range(len(st.session_state.projeler)), format_func=lambda x: f"{st.session_state.projeler[x]['Tarih']} - {st.session_state.projeler[x]['Proje']} ({st.session_state.projeler[x]['Müşteri']})")
        
        if st.button("Seçilen Kaydı Sil"):
            silinen = st.session_state.projeler.pop(silinecek_index)
            st.warning(f"'{silinen['Proje']}' kaydı silindi. Güncellemek için sayfayı yenileyebilirsiniz.")
            st.rerun()
    else:
        st.info("Düzenlenecek kayıt bulunmuyor.")
