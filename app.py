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
# 2. VERİ YÖNETİMİ (Session State Başlangıcı)
# ==========================================
if "projeler" not in st.session_state:
    st.session_state.projeler = [
        {"Tarih": "2026-06-01", "Ay": "2026-06", "Usta": "MEHMET BEKİROĞLU", "Proje": "Merkezi Sistem Tesisat", "Müşteri": "Ahmet Yılmaz", "Kolon": 2, "Ic_Tesisat": 3, "Durum": "Tamamlandı", "Tutar": 45000},
        {"Tarih": "2026-06-05", "Ay": "2026-06", "Usta": "MARTES HİLMİ NOKAY", "Proje": "Kombi Montaj", "Müşteri": "Mehmet Demir", "Kolon": 1, "Ic_Tesisat": 2, "Durum": "Devam Ediyor", "Tutar": 22000},
        {"Tarih": "2026-05-15", "Ay": "2026-05", "Usta": "MUSTAFA GÜL", "Proje": "Bireysel Doğalgaz", "Müşteri": "Ali Kaya", "Kolon": 1, "Ic_Tesisat": 1, "Durum": "Tamamlandı", "Tutar": 15000}
    ]

# ==========================================
# 3. YAN MENÜ: DÖVİZ & ALTIN KURU TAKİBİ
# ==========================================
st.sidebar.markdown("### 💱 Finansal Piyasalar")
st.sidebar.metric(label="ABD Doları (USD)", value="32.50 ₺", delta="+0.25%")
st.sidebar.metric(label="Euro (EUR)", value="35.20 ₺", delta="-0.10%")
st.sidebar.metric(label="Gram Altın", value="2,450.00 ₺", delta="+1.40%")
st.sidebar.markdown("---")
st.sidebar.info("Güneş Doğalgaz & Mühendislik\nOfis Otomasyonu v3.0")

# ==========================================
# 4. ANA EKRAN VE BAŞLIK
# ==========================================
st.title("☀️ Güneş Doğalgaz & Mühendislik")
st.subheader("Ofis Proje, Mali ve Usta Performans Takip Paneli")

# Sekmeler (Tabs)
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 İş / Proje Takibi", 
    "📈 Rapor ve Analiz Paneli", 
    "👷 Usta Raporları & PDF İndir", 
    "📅 Geçmiş ve Düzenleme"
])

# --- TAB 1: İŞ / PROJE TAKİBİ ---
with tab1:
    st.markdown("### Yeni Proje veya İş Kaydı Ekle")
    
    col1, col2 = st.columns(2)
    with col1:
        proje_adi = st.text_input("Proje / İş Adı")
        musteri_adi = st.text_input("Müşteri Adı Soyadı")
        usta_secim = st.selectbox("Görevli Usta", [
            "GÜNEŞ DOĞALGAZ GNS", "MARTES HİLMİ NOKAY", "MEHMET BEKİROĞLU", 
            "MEHMET YİĞİT", "MUHAMMET SÜT", "MUSTAFA GÜL", "SURİYELİ MUHAMMET", "VATAN SİNAN"
        ])
        is_tarihi = st.date_input("İş Tarihi", value=datetime.today())
    
    with col2:
        kolon_sayisi = st.number_input("Kolon Sayısı", min_value=0, step=1, value=1)
        ic_tesisat_sayisi = st.number_input("İç Tesisat Sayısı", min_value=0, step=1, value=0)
        durum = st.selectbox("İş Durumu", ["Devam Ediyor", "Tamamlandı", "Beklemede"])
        tutar = st.number_input("Proje Bedeli (TL)", min_value=0, step=1000, value=5000)
    
    if st.button("Kaydı Ekle"):
        if proje_adi and musteri_adi:
            ay_str = is_tarihi.strftime("%Y-%m")
            yeni_kayit = {
                "Tarih": str(is_tarihi),
                "Ay": ay_str,
                "Usta": usta_secim,
                "Proje": proje_adi,
                "Müşteri": musteri_adi,
                "Kolon": kolon_sayisi,
                "Ic_Tesisat": ic_tesisat_sayisi,
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
        df_all = pd.DataFrame(st.session_state.projeler)
        st.dataframe(df_all, use_container_width=True)
    else:
        st.info("Henüz kayıtlı bir proje bulunmuyor.")

# --- TAB 2: RAPOR VE ANALİZ PANELİ ---
with tab2:
    st.markdown("### 📈 Ofis Detaylı Mali ve Usta Performans Analiz Paneli")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        rapor_turu = st.radio("Raporlama Periyodu Seçin:", ["Aylık Raporlama", "Haftalık Raporlama"], horizontal=True)
    with col_p2:
        secilen_ay = st.selectbox("İncelemek İstediğiniz Mali Ayı Seçin:", ["2026-06", "2026-05", "2026-04"])

    df_main = pd.DataFrame(st.session_state.projeler)
    
    if not df_main.empty and "Ay" in df_main.columns:
        df_filt = df_main[df_main["Ay"] == secilen_ay]
    else:
        df_filt = pd.DataFrame(columns=["Tarih", "Ay", "Usta", "Proje", "Müşteri", "Kolon", "Ic_Tesisat", "Durum", "Tutar"])

    # Bu ayki ciro ve geçen aya göre yüzdelik değişim hesabı
    simdiki_ciro = df_filt["Tutar"].sum() if not df_filt.empty else 0
    
    # Geçen ayın cirosu hesabı
    if secilen_ay == "2026-06":
        gecen_ay = "2026-05"
    elif secilen_ay == "2026-05":
        gecen_ay = "2026-04"
    else:
        gecen_ay = "2026-03"
        
    df_gecen = df_main[df_main["Ay"] == gecen_ay] if not df_main.empty and "Ay" in df_main.columns else pd.DataFrame()
    gecen_ciro = df_gecen["Tutar"].sum() if not df_gecen.empty else 1 # Sıfıra bölünme hatası olmasın
    
    yuzde_degisim = ((simdiki_ciro - gecen_ciro) / gecen_ciro) * 100 if gecen_ciro > 0 else 0

    toplam_tahsil_edilen = 0 # Örnek tahsilat
    kalan_alacak = simdiki_ciro - toplam_tahsil_edilen

    # Metrik Kartları (Geçen aya göre yüzdelik değişim ile)
    m1, m2, m3 = st.columns(3)
    m1.metric(label=f"🔥 Toplam Ciro ({secilen_ay})", value=f"{simdiki_ciro:,.2f} ₺", delta=f"%{yuzde_degisim:+.1f} (Geçen Aya Göre)")
    m2.metric(label="✅ Toplam Tahsil Edilen", value=f"{toplam_tahsil_edilen:,.2f} ₺")
    m3.metric(label="🚨 Kalan Ofis Alacağı", value=f"{kalan_alacak:,.2f} ₺")

    st.markdown("---")
    st.subheader(f"📊 {secilen_ay} Dönemi Usta Detaylı İş / İçerik Dağılım Sayıları")

    if not df_filt.empty:
        # Usta bazlı özet tablo oluşturma
        usta_ozet = df_filt.groupby("Usta").agg(
            Toplam_Is=("Proje", "count"),
            Kolon_Sayisi=("Kolon", "sum"),
            Ic_Tesisat_Sayisi=("Ic_Tesisat", "sum"),
            Urettigi_Ciro=("Tutar", "sum")
        ).reset_index()
        
        usta_ozet.rename(columns={
            "Usta": "Usta Adı",
            "Toplam_Is": "Toplam İş (Adet)",
            "Kolon_Sayisi": "Kolon Sayısı",
            "Ic_Tesisat_Sayisi": "İç Tesisat Sayısı",
            "Urettigi_Ciro": "Ürettiği Toplam Ciro (TL)"
        }, inplace=True)
    else:
        usta_ozet = pd.DataFrame(columns=["Usta Adı", "Toplam İş (Adet)", "Kolon Sayısı", "İç Tesisat Sayısı", "Ürettiği Toplam Ciro (TL)"])

    col_chart, col_table = st.columns([1.3, 1])

    with col_chart:
        st.markdown("##### Ustaların Kolon ve İç Tesisat Dağılım Grafiği")
        if not usta_ozet.empty:
            chart_data = usta_ozet.set_index("Usta Adı")[["Kolon Sayısı", "İç Tesisat Sayısı"]]
            st.bar_chart(chart_data)
        else:
            st.info("Bu aya ait grafik verisi bulunmuyor.")

    with col_table:
        st.markdown("##### Net Adet Raporlama Tablosu")
        if not usta_ozet.empty:
            st.dataframe(usta_ozet, use_container_width=True, hide_index=True)
        else:
            st.info("Bu aya ait kayıt bulunmuyor.")

# --- TAB 3: USTA RAPORLARI & PDF İNDİR ---
with tab3:
    st.markdown("### 👷 Usta Bazlı Performans ve Proje Raporları")
    st.write("Her bir usta bu ay kaç proje yapmış, ne kadar ciro üretmiş buradan inceleyebilir ve raporu indirebilirsiniz.")

    secilen_usta = st.selectbox("Raporunu Görmek İstediğiniz Ustayı Seçin:", [
        "MEHMET BEKİROĞLU", "MARTES HİLMİ NOKAY", "GÜNEŞ DOĞALGAZ GNS", 
        "MEHMET YİĞİT", "MUHAMMET SÜT", "MUSTAFA GÜL", "SURİYELİ MUHAMMET", "VATAN SİNAN"
    ])
    
    secilen_usta_ay = st.selectbox("Rapor Ayı Seçin:", ["2026-06", "2026-05", "2026-04"], key="usta_pdf_ay")

    df_m_all = pd.DataFrame(st.session_state.projeler)
    if not df_m_all.empty:
        usta_filt = df_m_all[(df_m_all["Usta"] == secilen_usta) & (df_m_all["Ay"] == secilen_usta_ay)]
    else:
        usta_filt = pd.DataFrame()

    st.markdown(f"#### 👤 {secilen_usta} - {secilen_usta_ay} Dönem Raporu")
    
    if not usta_filt.empty:
        u_toplam_is = len(usta_filt)
        u_toplam_ciro = usta_filt["Tutar"].sum()
        u_kolon = usta_filt["Kolon"].sum()
        u_tesisat = usta_filt["Ic_Tesisat"].sum()

        uc1, uc2, uc3, uc4 = st.columns(4)
        uc1.metric("Toplam Proje Adedi", u_toplam_is)
        uc2.metric("Toplam Ürettiği Ciro", f"{u_toplam_ciro:,.2f} ₺")
        uc3.metric("Toplam Kolon", u_kolon)
        uc4.metric("Toplam İç Tesisat", u_tesisat)

        st.markdown("##### Yapılan Projelerin Detay Listesi:")
        st.dataframe(usta_filt[["Tarih", "Proje", "Müşteri", "Kolon", "Ic_Tesisat", "Durum", "Tutar"]], use_container_width=True, hide_index=True)

        # PDF veya Rapor İndirme İçeriği Hazırlama
        rapor_metni = f"""
GÜNEŞ DOĞALGAZ & MÜHENDİSLİK - USTA PERFORMANS RAPORU
--------------------------------------------------
Usta Adı: {secilen_usta}
Rapor Dönemi: {secilen_usta_ay}
Toplam Proje Sayısı: {u_toplam_is}
Toplam Kolon Sayısı: {u_kolon}
Toplam İç Tesisat Sayısı: {u_tesisat}
Ürettiği Toplam Ciro: {u_toplam_ciro:,.2f} TL
--------------------------------------------------
PROJE DETAYLARI:
"""
        for index, row in usta_filt.iterrows():
            rapor_metni += f"- Tarih: {row['Tarih']} | Proje: {row['Proje']} | Müşteri: {row['Müşteri']} | Tutar: {row['Tutar']} TL\n"

        st.download_button(
            label="📄 Usta Raporunu Metin/Yazıcı Dostu Formatında İndir (PDF İçin Yazdır)",
            data=rapor_metni,
            file_name=f"{secilen_usta}_{secilen_usta_ay}_raporu.txt",
            mime="text/plain"
        )
        st.info("💡 Not: İndirdiğiniz bu metin dosyasını açıp yazdır (Print) diyerek doğrudan PDF olarak kaydedebilirsiniz.")
    else:
        st.info(f"{secilen_usta} ustasının {secilen_usta_ay} dönemine ait kayıtlı projesi bulunmamaktadır.")

# --- TAB 4: GEÇMİŞ VE DÜZENLEME ---
with tab4:
    st.markdown("### 🕒 Geçmiş Tarihli Kayıtlar ve Yönetim")
    st.write("Buradan geçmiş tarihlere ait projeleri inceleyebilir veya listeden silebilirsiniz.")
    
    if st.session_state.projeler:
        silinecek_index = st.selectbox(
            "Silinecek Projeyi Seçin", 
            options=range(len(st.session_state.projeler)), 
            format_func=lambda x: f"{st.session_state.projeler[x]['Ay']} | {st.session_state.projeler[x]['Usta']} - {st.session_state.projeler[x]['Proje']} ({st.session_state.projeler[x]['Müşteri']})"
        )
        
        if st.button("Seçilen Kaydı Sil"):
            silinen = st.session_state.projeler.pop(silinecek_index)
            st.warning(f"'{silinen['Proje']}' kaydı silindi.")
            st.rerun()
    else:
        st.info("Düzenlenecek kayıt bulunmuyor.")
