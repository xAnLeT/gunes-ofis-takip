import io
import re
import unicodedata
from datetime import date, datetime

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


st.set_page_config(
    page_title="Güneş Doğalgaz | Ofis Takip Paneli",
    page_icon="🔧",
    layout="wide",
)

USTALAR = [
    "GÜNEŞ DOĞALGAZ GNS",
    "MARTES HİLMİ NOKAY",
    "MEHMET BEKİROĞLU",
    "MEHMET YİĞİT",
    "MUHAMMET SÜT",
    "MUSTAFA GÜL",
    "SURİYELİ MUHAMMET",
    "VATAN SİNAN",
]

COLUMNS = [
    "Tarih", "Ay", "Usta", "Proje", "Müşteri", "Kolon", "Ic_Tesisat",
    "Durum", "Tutar", "Tahsilat",
]

ROLE_LABELS = {
    "admin": "Admin",
    "yonetici": "Yönetici",
    "yonetici_yardimcisi": "Yönetici Yardımcısı",
    "personel": "Personel",
}

# İlk kurulum için örnek hesaplar. Canlı yayında bunları Streamlit Secrets'e taşıyın.
DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "admin", "name": "Sistem Yöneticisi"},
    "yonetici": {"password": "yonetici123", "role": "yonetici", "name": "Ofis Yöneticisi"},
    "yardimci": {"password": "yardimci123", "role": "yonetici_yardimcisi", "name": "Yönetici Yardımcısı"},
    "personel": {"password": "personel123", "role": "personel", "name": "Ofis Personeli"},
}


def tr_money(value: float) -> str:
    """TL biçiminde okunabilir para değeri döndürür."""
    return f"{float(value):,.2f} ₺"


def ascii_text(value: object) -> str:
    """Standart PDF fontları için Türkçe karakterleri güvenle sadeleştirir."""
    replacements = str.maketrans({"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ü": "u", "Ü": "U", "ö": "o", "Ö": "O", "ç": "c", "Ç": "C"})
    return unicodedata.normalize("NFKD", str(value).translate(replacements)).encode("ascii", "ignore").decode("ascii")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_text(value)).strip("_")


def get_dataframe() -> pd.DataFrame:
    df = pd.DataFrame(st.session_state.projeler, columns=COLUMNS)
    if df.empty:
        return df
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    for column in ["Kolon", "Ic_Tesisat", "Tutar", "Tahsilat"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    df["Ay"] = df["Tarih"].dt.strftime("%Y-%m")
    df["Kalan_Alacak"] = (df["Tutar"] - df["Tahsilat"]).clip(lower=0)
    return df


def available_months(df: pd.DataFrame) -> list[str]:
    months = sorted(df["Ay"].dropna().unique().tolist(), reverse=True) if not df.empty else []
    current = date.today().strftime("%Y-%m")
    return months if months else [current]


def previous_month(month: str) -> str:
    return str(pd.Period(month, freq="M") - 1)


def calculate_change(current: float, previous: float) -> str:
    if previous == 0:
        return "Yeni dönem" if current > 0 else "%0,0"
    return f"%{((current - previous) / previous) * 100:+.1f}"


def can_manage_records(role: str) -> bool:
    """Kayıt düzenleme/silme yetkisi yalnızca yönetim rollerindedir."""
    return role in {"admin", "yonetici", "yonetici_yardimcisi"}


def render_login() -> None:
    """Uygulama açılmadan önce gösterilen rol bazlı giriş ekranı."""
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none;}
        .login-card {max-width: 470px; margin: 8vh auto; padding: 2.25rem;
            border-radius: 20px; background: linear-gradient(145deg,#103c4a,#167d9a);
            color: white; box-shadow: 0 18px 45px rgba(11,55,68,.28);}
        .login-card h1 {font-size: 2rem; margin-bottom: .35rem;}
        .login-card p {opacity: .9;}
        </style>
        <div class="login-card"><h1>☀️ Güneş Doğalgaz</h1>
        <p>Ofis takip sistemine güvenli giriş yapın.</p></div>
    """, unsafe_allow_html=True)
    _, middle, _ = st.columns([1, 1.35, 1])
    with middle:
        with st.form("login_form"):
            username = st.text_input("Kullanıcı adı", autocomplete="username")
            password = st.text_input("Şifre", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
        if submitted:
            user = st.session_state.users.get(username.strip().lower())
            if user and password == user["password"]:
                st.session_state.current_user = {"username": username.strip().lower(), **user}
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")
        with st.expander("İlk kurulum demo hesapları"):
            st.caption("Admin: admin / admin123 · Yönetici: yonetici / yonetici123 · Yardımcı: yardimci / yardimci123 · Personel: personel / personel123")


def render_tv_dashboard() -> None:
    """TV'lerde okunabilir büyük göstergeli, yalnızca görüntüleme ekranı."""
    st.markdown("""
        <style>
        [data-testid="stSidebar"], [data-testid="stHeader"] {display: none;}
        .block-container {padding: 1.5rem 3rem 2rem; max-width: 100%;}
        [data-testid="stMetricValue"] {font-size: 2.7rem;}
        [data-testid="stMetricLabel"] {font-size: 1.15rem;}
        h1 {font-size: 2.5rem !important;}
        </style>
    """, unsafe_allow_html=True)
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.title("☀️ Güneş Doğalgaz | Canlı Ofis Ekranı")
        st.caption(f"Son görüntüleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    with top_right:
        if st.button("TV Modundan Çık", use_container_width=True):
            st.session_state.tv_mode = False
            st.rerun()
    df = get_dataframe()
    month = available_months(df)[0]
    current = df[df["Ay"] == month] if not df.empty else pd.DataFrame(columns=COLUMNS)
    revenue = current["Tutar"].sum() if not current.empty else 0
    collection = current["Tahsilat"].sum() if not current.empty else 0
    active = len(current[current["Durum"] == "Devam Ediyor"]) if not current.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"{month} Toplam Ciro", tr_money(revenue))
    k2.metric("Tahsil Edilen", tr_money(collection))
    k3.metric("Kalan Ofis Alacağı", tr_money(revenue - collection))
    k4.metric("Devam Eden İş", f"{active} adet")
    st.markdown("---")
    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Usta Performansı")
        if not current.empty:
            tv_summary = current.groupby("Usta", as_index=False).agg(Ciro=("Tutar", "sum"), Kolon=("Kolon", "sum"), **{"İç Tesisat": ("Ic_Tesisat", "sum")}).sort_values("Ciro", ascending=False)
            st.bar_chart(tv_summary.set_index("Usta")[["Ciro"]], color="#2A9D8F")
            st.dataframe(tv_summary, hide_index=True, use_container_width=True, column_config={"Ciro": st.column_config.NumberColumn(format="%.2f ₺")})
        else:
            st.info("Bu ay için proje bulunmuyor.")
    with right:
        st.subheader("Açık Projeler")
        active_projects = current[current["Durum"] != "Tamamlandı"] if not current.empty else pd.DataFrame()
        if active_projects.empty:
            st.success("Gösterilecek açık proje yok.")
        else:
            st.dataframe(active_projects[["Usta", "Proje", "Müşteri", "Durum", "Tutar"]], hide_index=True, use_container_width=True, column_config={"Tutar": st.column_config.NumberColumn("Ciro", format="%.2f ₺")})
    st.caption("TV ekranını tam ekran kullanmak için tarayıcıda F11 tuşuna basın. Veriler yeni kayıt eklendiğinde yenilenir.")


def build_master_pdf(usta: str, month: str, records: pd.DataFrame) -> bytes:
    """Seçili usta ve ay için indirilebilir gerçek PDF üretir."""
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=1.2 * cm, leftMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("GUNES DOGALGAZ & MUHENDISLIK", styles["Title"]),
        Paragraph("USTA PERFORMANS VE PROJE RAPORU", styles["Heading2"]),
        Spacer(1, 0.25 * cm),
        Paragraph(f"Usta: <b>{ascii_text(usta)}</b> &nbsp;&nbsp; Rapor donemi: <b>{month}</b>", styles["Normal"]),
        Paragraph(f"Rapor tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles["Normal"]),
        Spacer(1, 0.35 * cm),
    ]

    total_revenue = records["Tutar"].sum()
    total_collection = records["Tahsilat"].sum()
    summary = [
        ["Toplam Proje", "Toplam Ciro", "Tahsilat", "Kalan Alacak", "Kolon", "Ic Tesisat"],
        [
            str(len(records)), tr_money(total_revenue), tr_money(total_collection),
            tr_money((total_revenue - total_collection)), str(int(records["Kolon"].sum())),
            str(int(records["Ic_Tesisat"].sum())),
        ],
    ]
    summary_table = Table(summary, colWidths=[2.3 * cm, 3.1 * cm, 3 * cm, 3.2 * cm, 1.7 * cm, 2.2 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B9C6CC")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F3F7F8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([summary_table, Spacer(1, 0.45 * cm), Paragraph("PROJE DETAYLARI", styles["Heading3"])])

    detail = [["Tarih", "Proje / Musteri", "Durum", "Kolon", "Ic Tesisat", "Ciro", "Tahsilat"]]
    for _, row in records.sort_values("Tarih").iterrows():
        detail.append([
            row["Tarih"].strftime("%d.%m.%Y"),
            f"{ascii_text(row['Proje'])}\n{ascii_text(row['Müşteri'])}",
            ascii_text(row["Durum"]), str(int(row["Kolon"])), str(int(row["Ic_Tesisat"])),
            tr_money(row["Tutar"]), tr_money(row["Tahsilat"]),
        ])
    detail_table = Table(detail, repeatRows=1, colWidths=[2 * cm, 5.2 * cm, 2.4 * cm, 1.3 * cm, 1.8 * cm, 2.8 * cm, 2.8 * cm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#167D9A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C7D1D5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(detail_table)
    document.build(story)
    return buffer.getvalue()


if "projeler" not in st.session_state:
    st.session_state.projeler = [
        {"Tarih": "2026-06-01", "Ay": "2026-06", "Usta": "MEHMET BEKİROĞLU", "Proje": "Merkezi Sistem Tesisat", "Müşteri": "Ahmet Yılmaz", "Kolon": 2, "Ic_Tesisat": 3, "Durum": "Tamamlandı", "Tutar": 45000, "Tahsilat": 30000},
        {"Tarih": "2026-06-05", "Ay": "2026-06", "Usta": "MARTES HİLMİ NOKAY", "Proje": "Kombi Montaj", "Müşteri": "Mehmet Demir", "Kolon": 1, "Ic_Tesisat": 2, "Durum": "Devam Ediyor", "Tutar": 22000, "Tahsilat": 7000},
        {"Tarih": "2026-05-15", "Ay": "2026-05", "Usta": "MUSTAFA GÜL", "Proje": "Bireysel Doğalgaz", "Müşteri": "Ali Kaya", "Kolon": 1, "Ic_Tesisat": 1, "Durum": "Tamamlandı", "Tutar": 15000, "Tahsilat": 15000},
    ]

if "users" not in st.session_state:
    st.session_state.users = DEFAULT_USERS.copy()
if "tv_mode" not in st.session_state:
    st.session_state.tv_mode = False

if "current_user" not in st.session_state:
    render_login()
    st.stop()

current_user = st.session_state.current_user
current_role = current_user["role"]

if st.session_state.tv_mode:
    render_tv_dashboard()
    st.stop()

st.sidebar.markdown("### 💼 Ofis Takip Paneli")
st.sidebar.caption("Güneş Doğalgaz & Mühendislik")
st.sidebar.markdown("---")
st.sidebar.success(f"{current_user['name']}\n\nRol: {ROLE_LABELS[current_role]}")
if st.sidebar.button("📺 TV Modunu Aç", use_container_width=True):
    st.session_state.tv_mode = True
    st.rerun()
if st.sidebar.button("↪ Çıkış Yap", use_container_width=True):
    del st.session_state.current_user
    st.rerun()
st.sidebar.markdown("---")
st.sidebar.info("Ciro, tahsilat, kalan alacak ve usta performansını tek ekrandan takip edin.")

st.title("☀️ Güneş Doğalgaz & Mühendislik")
st.caption(f"Proje, mali durum ve usta performans takip paneli | Giriş: {current_user['name']} ({ROLE_LABELS[current_role]})")

tab1, tab2, tab3, tab4 = st.tabs(["🚀 İş / Proje Takibi", "📈 Rapor ve Analiz", "👷 Usta Raporları ve PDF", "🕘 Kayıt Yönetimi"])

with tab1:
    st.subheader("Yeni Proje veya İş Kaydı")
    with st.form("new_project", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            proje = st.text_input("Proje / İş adı *")
            musteri = st.text_input("Müşteri adı soyadı *")
            usta = st.selectbox("Görevli usta", USTALAR)
            is_tarihi = st.date_input("İş tarihi", value=date.today())
        with c2:
            kolon = st.number_input("Kolon sayısı", min_value=0, step=1, value=1)
            ic_tesisat = st.number_input("İç tesisat sayısı", min_value=0, step=1, value=0)
            durum = st.selectbox("İş durumu", ["Devam Ediyor", "Tamamlandı", "Beklemede"])
            tutar = st.number_input("Proje bedeli (TL)", min_value=0.0, step=1000.0, value=5000.0)
            tahsilat = st.number_input("Tahsil edilen tutar (TL)", min_value=0.0, max_value=float(tutar), step=1000.0, value=0.0)
        submitted = st.form_submit_button("Kaydı Ekle", type="primary")
    if submitted:
        if not proje.strip() or not musteri.strip():
            st.warning("Proje adı ve müşteri bilgisi zorunludur.")
        else:
            st.session_state.projeler.append({
                "Tarih": str(is_tarihi), "Ay": is_tarihi.strftime("%Y-%m"), "Usta": usta,
                "Proje": proje.strip(), "Müşteri": musteri.strip(), "Kolon": kolon,
                "Ic_Tesisat": ic_tesisat, "Durum": durum, "Tutar": tutar, "Tahsilat": tahsilat,
            })
            st.success(f"{proje} projesi kaydedildi.")

    st.markdown("---")
    st.subheader("Tüm Kayıtlar")
    overview = get_dataframe()
    if overview.empty:
        st.info("Henüz kayıtlı proje yok.")
    else:
        st.dataframe(
            overview[["Tarih", "Ay", "Usta", "Proje", "Müşteri", "Kolon", "Ic_Tesisat", "Durum", "Tutar", "Tahsilat", "Kalan_Alacak"]],
            column_config={
                "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                "Ic_Tesisat": "İç Tesisat",
                "Tutar": st.column_config.NumberColumn("Proje Bedeli", format="%.2f ₺"),
                "Tahsilat": st.column_config.NumberColumn("Tahsilat", format="%.2f ₺"),
                "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
            }, hide_index=True, use_container_width=True,
        )

with tab2:
    st.subheader("Mali Durum ve Usta Performans Analizi")
    df = get_dataframe()
    months = available_months(df)
    selected_month = st.selectbox("Rapor dönemi", months, key="analysis_month")
    current = df[df["Ay"] == selected_month].copy() if not df.empty else pd.DataFrame(columns=COLUMNS)
    last_month = previous_month(selected_month)
    previous = df[df["Ay"] == last_month] if not df.empty else pd.DataFrame(columns=COLUMNS)
    revenue = current["Tutar"].sum() if not current.empty else 0
    collection = current["Tahsilat"].sum() if not current.empty else 0
    receivable = revenue - collection
    prev_revenue = previous["Tutar"].sum() if not previous.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Ciro", tr_money(revenue), delta=calculate_change(revenue, prev_revenue), delta_color="normal", help=f"{last_month} cirosuna göre değişim")
    k2.metric("Toplam Tahsil Edilen", tr_money(collection))
    k3.metric("Kalan Ofis Alacağı", tr_money(receivable))
    k4.metric("Toplam Proje", f"{len(current)} adet")

    st.markdown("---")
    st.subheader(f"{selected_month} Usta İş Dağılımı")
    if current.empty:
        st.info("Bu dönemde analiz edilecek kayıt bulunmuyor.")
    else:
        master_summary = current.groupby("Usta", as_index=False).agg(
            **{"Toplam İş": ("Proje", "count"), "Kolon Sayısı": ("Kolon", "sum"),
               "İç Tesisat Sayısı": ("Ic_Tesisat", "sum"), "Ürettiği Ciro": ("Tutar", "sum"),
               "Tahsilat": ("Tahsilat", "sum"), "Kalan Alacak": ("Kalan_Alacak", "sum")}
        ).sort_values("Ürettiği Ciro", ascending=False)
        left, right = st.columns([1.15, 1])
        with left:
            st.markdown("##### Kolon ve iç tesisat grafiği")
            st.bar_chart(master_summary.set_index("Usta")[["Kolon Sayısı", "İç Tesisat Sayısı"]], color=["#167D9A", "#F4A261"])
            st.markdown("##### Ustaların ürettiği ciro")
            st.bar_chart(master_summary.set_index("Usta")[["Ürettiği Ciro"]], color="#2A9D8F")
        with right:
            st.markdown("##### Usta bilgi ve performans tablosu")
            st.dataframe(master_summary, column_config={
                "Ürettiği Ciro": st.column_config.NumberColumn(format="%.2f ₺"),
                "Tahsilat": st.column_config.NumberColumn(format="%.2f ₺"),
                "Kalan Alacak": st.column_config.NumberColumn(format="%.2f ₺"),
            }, hide_index=True, use_container_width=True)

with tab3:
    st.subheader("Usta Bazlı Proje Raporu")
    df = get_dataframe()
    months = available_months(df)
    a, b = st.columns(2)
    with a:
        selected_master = st.selectbox("Usta seçin", USTALAR)
    with b:
        master_month = st.selectbox("Rapor ayı", months, key="master_month")
    master_records = df[(df["Usta"] == selected_master) & (df["Ay"] == master_month)].copy() if not df.empty else pd.DataFrame(columns=COLUMNS)
    st.markdown(f"#### {selected_master} | {master_month}")
    if master_records.empty:
        st.info("Bu usta için seçilen ayda proje kaydı bulunmuyor.")
    else:
        revenue = master_records["Tutar"].sum()
        collection = master_records["Tahsilat"].sum()
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("Proje", f"{len(master_records)} adet")
        p2.metric("Ürettiği Ciro", tr_money(revenue))
        p3.metric("Tahsilat", tr_money(collection))
        p4.metric("Kolon", int(master_records["Kolon"].sum()))
        p5.metric("İç Tesisat", int(master_records["Ic_Tesisat"].sum()))
        st.markdown("##### Yaptığı projeler")
        st.dataframe(master_records[["Tarih", "Proje", "Müşteri", "Durum", "Kolon", "Ic_Tesisat", "Tutar", "Tahsilat", "Kalan_Alacak"]], column_config={
            "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
            "Ic_Tesisat": "İç Tesisat",
            "Tutar": st.column_config.NumberColumn("Ciro", format="%.2f ₺"),
            "Tahsilat": st.column_config.NumberColumn(format="%.2f ₺"),
            "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
        }, hide_index=True, use_container_width=True)
        pdf = build_master_pdf(selected_master, master_month, master_records)
        st.download_button("📄 Usta raporunu PDF indir", data=pdf, file_name=f"{safe_filename(selected_master)}_{master_month}_raporu.pdf", mime="application/pdf", type="primary")

with tab4:
    if not can_manage_records(current_role):
        st.subheader("Kayıt Yönetimi")
        st.warning("Kayıt düzenleme ve silme sadece Admin, Yönetici ve Yönetici Yardımcısı rollerine açıktır.")
    else:
        st.subheader("Kayıt Düzenleme ve Silme")
        st.caption("Kayıt seçin, değerleri düzenleyin veya kaydı silin.")
        if not st.session_state.projeler:
            st.info("Düzenlenecek kayıt bulunmuyor.")
        else:
            options = list(range(len(st.session_state.projeler)))
            selected_index = st.selectbox("Kayıt", options, format_func=lambda i: f"{st.session_state.projeler[i]['Tarih']} | {st.session_state.projeler[i]['Usta']} | {st.session_state.projeler[i]['Proje']}")
            record = st.session_state.projeler[selected_index]
            with st.form("edit_project"):
                e1, e2 = st.columns(2)
                with e1:
                    edit_date = st.date_input("İş tarihi", value=pd.to_datetime(record["Tarih"]).date(), key="edit_date")
                    edit_project = st.text_input("Proje / İş adı", value=record["Proje"])
                    edit_customer = st.text_input("Müşteri", value=record["Müşteri"])
                    edit_master = st.selectbox("Usta", USTALAR, index=USTALAR.index(record["Usta"]) if record["Usta"] in USTALAR else 0)
                with e2:
                    statuses = ["Devam Ediyor", "Tamamlandı", "Beklemede"]
                    edit_status = st.selectbox("Durum", statuses, index=statuses.index(record["Durum"]) if record["Durum"] in statuses else 0)
                    edit_column = st.number_input("Kolon", min_value=0, step=1, value=int(record["Kolon"]))
                    edit_installation = st.number_input("İç tesisat", min_value=0, step=1, value=int(record["Ic_Tesisat"]))
                    edit_amount = st.number_input("Proje bedeli (TL)", min_value=0.0, value=float(record["Tutar"]), step=1000.0)
                    edit_collection = st.number_input("Tahsilat (TL)", min_value=0.0, max_value=float(edit_amount), value=min(float(record.get("Tahsilat", 0)), float(edit_amount)), step=1000.0)
                save = st.form_submit_button("Değişiklikleri Kaydet", type="primary")
            if save:
                st.session_state.projeler[selected_index] = {"Tarih": str(edit_date), "Ay": edit_date.strftime("%Y-%m"), "Usta": edit_master, "Proje": edit_project, "Müşteri": edit_customer, "Kolon": edit_column, "Ic_Tesisat": edit_installation, "Durum": edit_status, "Tutar": edit_amount, "Tahsilat": edit_collection}
                st.success("Kayıt güncellendi.")
                st.rerun()
            if current_role in {"admin", "yonetici"} and st.button("Seçili kaydı sil", type="secondary"):
                removed = st.session_state.projeler.pop(selected_index)
                st.warning(f"{removed['Proje']} kaydı silindi.")
                st.rerun()

        if current_role == "admin":
            st.markdown("---")
            st.subheader("Kullanıcı Yönetimi")
            with st.form("create_user", clear_on_submit=True):
                u1, u2, u3, u4 = st.columns(4)
                username = u1.text_input("Kullanıcı adı")
                name = u2.text_input("Ad soyad")
                password = u3.text_input("İlk şifre", type="password")
                role = u4.selectbox("Rol", list(ROLE_LABELS), format_func=lambda r: ROLE_LABELS[r])
                create_user = st.form_submit_button("Kullanıcı Ekle")
            if create_user:
                key = username.strip().lower()
                if not key or not name.strip() or len(password) < 6:
                    st.error("Kullanıcı adı, ad soyad ve en az 6 karakterli şifre girin.")
                elif key in st.session_state.users:
                    st.error("Bu kullanıcı adı zaten var.")
                else:
                    st.session_state.users[key] = {"password": password, "role": role, "name": name.strip()}
                    st.success(f"{name} kullanıcısı eklendi.")
            user_rows = pd.DataFrame([
                {"Kullanıcı Adı": username, "Ad Soyad": data["name"], "Rol": ROLE_LABELS[data["role"]]}
                for username, data in st.session_state.users.items()
            ])
            st.dataframe(user_rows, hide_index=True, use_container_width=True)
            st.caption("Bu başlangıç sürümünde kullanıcılar oturum belleğinde tutulur. Kalıcı ve güvenli kullanım için kullanıcıları veritabanında saklayıp şifreleri hash'leyin.")
