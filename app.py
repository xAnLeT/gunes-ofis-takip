import pandas as pd
import streamlit as st

# Sayfa yapılandırması
st.set_page_config(
    page_title="Güneş Doğalgaz & Mühendislik - Ofis Takip V2",
    page_icon="🔥",
    layout="wide",
)

# Görseldeki menü tasarımına ve koyu temaya birebir uyan özel CSS stilleri
st.markdown(
    """
    <style>
    /* Ana uygulama arka planı */
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    
    /* Sidebar (Sol Menü) tasarımı */
    [data-testid="stSidebar"] {
        background-color: #0d1117;
        padding-top: 10px;
        border-right: 1px solid #21262d;
    }
    
    /* Sidebar içerisindeki başlık */
    .sidebar-title {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 600;
        padding: 10px 15px;
        letter-spacing: 0.5px;
    }
    
    /* Streamlit butonlarının sol menüdeki görünümü (Görseldeki gibi yuvarlak ve şık) */
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        background-color: transparent;
        color: #c9d1d9;
        border: none;
        border-radius: 12px;
        padding: 12px 18px;
        text-align: left;
        font-weight: 500;
        font-size: 15px;
        margin-bottom: 6px;
        transition: all 0.2s ease-in-out;
    }
    
    /* Butonların üzerine gelindiğinde (Hover) */
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #161b22;
        color: #ffffff;
        border: none;
    }
    
    /* Kart ve kutu stilleri */
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- SESSION STATE BAŞLANGIÇ DEĞERLERİ ---
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "reports" not in st.session_state:
    st.session_state.reports = [
        {
            "id": 1,
            "title": "Ocak Ayı Mekanik Tesisat Raporu",
            "date": "2026-01-15",
            "kategori": "Tesisat",
        },
        {
            "id": 2,
            "title": "Şubat Ayı Doğalgaz Proje Özeti",
            "date": "2026-02-10",
            "kategori": "Doğalgaz",
        },
        {
            "id": 3,
            "title": "Mart Ayı Saha Bakım Raporu",
            "date": "2026-03-05",
            "kategori": "Bakım",
        },
    ]

if "records" not in st.session_state:
    st.session_state.records = [
        {
            "id": 1,
            "musteri": "Ahmet Yılmaz",
            "is_turu": "Doğalgaz Proje",
            "tutar": "12.000 TL",
            "durum": "Tamamlandı",
        },
        {
            "id": 2,
            "musteri": "Mehmet Demir",
            "is_turu": "Kalorifer Tesisatı",
            "tutar": "18.500 TL",
            "durum": "Devam Ediyor",
        },
    ]

if "masters" not in st.session_state:
    st.session_state.masters = [
        {
            "id": 1,
            "ad": "Kadir Usta",
            "uzmanlik": "Doğalgaz Tesisat",
            "telefon": "0532 000 00 01",
        },
        {
            "id": 2,
            "ad": "Hasan Usta",
            "uzmanlik": "Mekanik Sistemler",
            "telefon": "0533 111 11 02",
        },
    ]

# --- SOL MENÜ (SİDEBAR) ---
with st.sidebar:
    st.markdown(
        '<div class="sidebar-title">🔥 Güneş Doğalgaz</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Görseldeki düzene göre butonlar ve aktif sayfa gösterimi
    dash_label = (
        "🗂️  Dashboard  ›"
        if st.session_state.page == "Dashboard"
        else "🗂️  Dashboard"
    )
    kayit_label = (
        "📋  Kayıtlar"
        if st.session_state.page != "Kayıtlar"
        else "📋  Kayıtlar (Aktif)"
    )
    usta_label = (
        "👷  Ustalar"
        if st.session_state.page != "Ustalar"
        else "👷  Ustalar (Aktif)"
    )
    rapor_label = (
        "📊  Raporlar"
        if st.session_state.page != "Raporlar"
        else "📊  Raporlar (Aktif)"
    )
    ayar_label = (
        "⚙️  Ayarlar"
        if st.session_state.page != "Ayarlar"
        else "⚙️  Ayarlar (Aktif)"
    )

    if st.button(dash_label, key="nav_dash"):
        st.session_state.page = "Dashboard"
        st.rerun()

    if st.button(kayit_label, key="nav_kayit"):
        st.session_state.page = "Kayıtlar"
        st.rerun()

    if st.button(usta_label, key="nav_usta"):
        st.session_state.page = "Ustalar"
        st.rerun()

    if st.button(rapor_label, key="nav_rapor"):
        st.session_state.page = "Raporlar"
        st.rerun()

    if st.button(ayar_label, key="nav_ayar"):
        st.session_state.page = "Ayarlar"
        st.rerun()

    st.markdown("---")
    st.caption("v2.2 Ofis Takip Otomasyonu")

# --- SAYFA İÇERİKLERİ ---
current_page = st.session_state.page

if current_page == "Dashboard":
    st.title("🗂️ Dashboard - Genel Bakış")
    st.write(
        "Güneş Doğalgaz & Mühendislik ofis operasyonları ve özet göstergeler."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Toplam Proje / Kayıt",
            value=len(st.session_state.records),
            delta="+1 bu hafta",
        )
    with col2:
        st.metric(
            label="Kayıtlı Raporlar",
            value=len(st.session_state.reports),
            delta="Güncel",
        )
    with col3:
        st.metric(
            label="Aktif Ustalar",
            value=len(st.session_state.masters),
            delta="Saha Ekibi",
        )
    with col4:
        st.metric(
            label="Haftalık Gelir Durumu",
            value="10,000 TL",
            delta="Standart",
        )

    st.markdown("---")
    st.subheader("Son Eklenen Kayıtlar ve Projeler")
    if st.session_state.records:
        df_rec = pd.DataFrame(st.session_state.records)
        st.dataframe(df_rec, use_container_width=True)
    else:
        st.info("Henüz kayıt eklenmemiş.")

elif current_page == "Kayıtlar":
    st.title("📋 Kayıtlar ve Proje Yönetimi")
    st.write(
        "Ofis bünyesindeki müşteri kayıtlarını, tesisat ve doğalgaz projelerini buradan yönetebilirsiniz."
    )

    with st.form("yeni_kayit_formu"):
        st.subheader("Yeni Kayıt Ekle")
        col_a, col_b = st.columns(2)
        with col_a:
            yeni_musteri = st.text_input("Müşteri Adı Soyadı")
            yeni_tur = st.selectbox(
                "İş Türü",
                [
                    "Doğalgaz Proje",
                    "Kalorifer Tesisatı",
                    "Kombi Bakım",
                    "Mekanik Tesisat",
                ],
            )
        with col_b:
            yeni_tutar = st.text_input("Tutar / Bütçe", "0 TL")
            yeni_durum = st.selectbox(
                "Durum", ["Beklemede", "Devam Ediyor", "Tamamlandı"]
            )

        submitted = st.form_submit_button("Kayıt Ekle")
        if submitted and yeni_musteri:
            yeni_id = (
                max([r["id"] for r in st.session_state.records], default=0) + 1
            )
            st.session_state.records.append(
                {
                    "id": yeni_id,
                    "musteri": yeni_musteri,
                    "is_turu": yeni_tur,
                    "tutar": yeni_tutar,
                    "durum": yeni_durum,
                }
            )
            st.success(f"'{yeni_musteri}' adlı müşteri başarıyla eklendi!")
            st.rerun()

    st.markdown("---")
    st.subheader("Mevcut Kayıt Listesi")
    if st.session_state.records:
        for rec in st.session_state.records:
            c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
            c1.write(f"**{rec['musteri']}**")
            c2.write(f"Tür: {rec['is_turu']}")
            c3.write(f"Tutar: {rec['tutar']}")
            if c4.button("Kayıt Sil", key=f"del_rec_{rec['id']}"):
                st.session_state.records = [
                    r for r in st.session_state.records if r["id"] != rec["id"]
                ]
                st.success("Kayıt silindi.")
                st.rerun()
    else:
        st.info("Kayıt bulunamadı.")

elif current_page == "Ustalar":
    st.title("👷 Ustalar ve Saha Ekibi")
    st.write("Mühendislik ve saha projelerinde görev alan ustalar.")

    with st.form("yeni_usta_formu"):
        st.subheader("Yeni Usta Ekle")
        u_ad = st.text_input("Usta Adı Soyadı")
        u_uzmanlik = st.text_input(
            "Uzmanlık Alanı", "Doğalgaz & Tesisat Montaj"
        )
        u_tel = st.text_input("Telefon Numarası", "05...")
        u_sub = st.form_submit_button("Usta Ekle")
        if u_sub and u_ad:
            u_id = (
                max([m["id"] for m in st.session_state.masters], default=0) + 1
            )
            st.session_state.masters.append(
                {"id": u_id, "ad": u_ad, "uzmanlik": u_uzmanlik, "telefon": u_tel}
            )
            st.success(f"'{u_ad}' usta kadroya eklendi.")
            st.rerun()

    st.markdown("---")
    for m in st.session_state.masters:
        col_m1, col_m2, col_m3 = st.columns([3, 3, 2])
        col_m1.write(f"**{m['ad']}** ({m['uzmanlik']})")
        col_m2.write(f"Tel: {m['telefon']}")
        if col_m3.button("Kadro Çıkar", key=f"del_master_{m['id']}"):
            st.session_state.masters = [
                item
                for item in st.session_state.masters
                if item["id"] != m["id"]
            ]
            st.success("Usta kadrodan çıkarıldı.")
            st.rerun()

elif current_page == "Raporlar":
    st.title("📊 Raporlar ve Yönetim Paneli")
    st.write(
        "Sistemde kayıtlı raporları inceleyebilir, yeni rapor oluşturabilir veya gereksiz raporları sistemden kaldırabilirsiniz."
    )

    # Yeni Rapor Ekleme Bölümü
    with st.expander("➕ Yeni Rapor Oluştur / Ekle"):
        with st.form("yeni_rapor_form"):
            rep_title = st.text_input("Rapor Başlığı")
            rep_kategori = st.selectbox(
                "Rapor Kategorisi", ["Tesisat", "Doğalgaz", "Bakım", "Finans"]
            )
            rep_date = st.date_input("Rapor Tarihi")
            rep_submit = st.form_submit_button("Raporu Kaydet")
            if rep_submit and rep_title:
                new_rep_id = (
                    max([r["id"] for r in st.session_state.reports], default=0)
                    + 1
                )
                st.session_state.reports.append(
                    {
                        "id": new_rep_id,
                        "title": rep_title,
                        "date": str(rep_date),
                        "kategori": rep_kategori,
                    }
                )
                st.success(f"'{rep_title}' başarıyla eklendi!")
                st.rerun()

    st.markdown("---")
    st.subheader("Mevcut Rapor Listesi ve Kaldırma İşlemleri")

    if not st.session_state.reports:
        st.info("Sistemde kayıtlı rapor bulunmuyor.")
    else:
        # Raporları listeleme ve kaldırma (silme) alanı
        for rep in st.session_state.reports:
            cols = st.columns([3, 2, 2, 2])
            cols.markdown(f"📄 **{rep['title']}**")
            cols.text(f"Kategori: {rep['kategori']}")
            cols.text(f"Tarih: {rep['date']}")

            # Her raporun yanına kaldırma (silme) butonu
            if cols.button("Raporu Kaldır", key=f"del_report_{rep['id']}"):
                st.session_state.reports = [
                    r for r in st.session_state.reports if r["id"] != rep["id"]
                ]
                st.warning(f"'{rep['title']}' sistemden kaldırıldı.")
                st.rerun()
            st.markdown("---")

elif current_page == "Ayarlar":
    st.title("⚙️ Ayarlar ve Sistem Yapılandırması")
    st.write("Ofis takip programı ayarları ve firma bilgileri.")

    st.text_input("Firma Unvanı", "Güneş Doğalgaz & Mühendislik")
    st.text_input("Yetkili Adı", "Anıl Levent Turhan")
    st.text_input("Sistem Sürümü", "v2.2-Stable")

    if st.button("Verileri Sıfırla / Fabrika Ayarları"):
        st.session_state.reports = []
        st.session_state.records = []
        st.session_state.masters = []
        st.success("Tüm veriler sıfırlandı.")
        st.rerun()
