import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. SİTE VE SAYfa YAPILANDIRMASI
# ==========================================
st.set_page_config(
    page_title="Güneş Doğalgaz & Mühendislik - Ofis Takip v2",
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
st.subheader("Ofis Proje ve İş Takip Paneli (v2)")

# Sekmeler (Tabs)
tab1, tab2, tab3 = st.tabs(["🚀 İş / Proje Takibi", "📊 Performans & Metrikler", "📅 Geçmiş ve Düzenleme"])

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

# --- TAB 2: PERFORMANS & METRİKLER ---
with tab2:
    st.markdown("### 📈 Ofis Performans ve İş Yükü Görselleştirme")
    
    if st.session_state.projeler:
        df_m = pd.DataFrame(st.session_state.projeler)
        
        toplam_is = len(df_m)
        tamamlanan = len(df_m[df_m["Durum"] == "Tamamlandı"])
        toplam_ciro = df_m["Tutar"].sum()
        
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Toplam Proje Sayısı", toplam_is)
        mcol2.metric("Tamamlanan İşler", tamamlanan)
        mcol3.metric("Toplam Ciro (TL)", f"{toplam_ciro:,.2f} TL")
        
        st.markdown("---")
        st.subheader("Durum Dağılım Grafiği")
        durum_sayilari = df_m["Durum"].value_counts()
        st.bar_chart(durum_sayilari)
    else:
        st.info("Metrikleri görüntülemek için önce proje eklemelisiniz.")

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
