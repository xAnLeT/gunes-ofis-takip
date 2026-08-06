import io
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


LOGO_PATH = Path(__file__).with_name("gunes_muhendislik_logo.jpg")


st.set_page_config(
    page_title="Güneş Doğalgaz | Ofis Takip Paneli",
    page_icon="🔧",
    layout="wide",
)

DEFAULT_USTALAR: list[str] = []

COLUMNS = [
    "Tarih", "Ay", "Usta", "Proje", "Müşteri", "Kolon", "Ic_Tesisat",
    "Durum", "Tutar", "Tahsilat", "Odeme_Yontemi", "Sayac_Seri_No",
    "Regulator_Durumu", "Proje_Gelis_Yolu", "Diger_Islemler", "Surec_Adimi", "Notlar", "Ofis_Borcu",
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


def pdf_money(value: float) -> str:
    """PDF'nin standart yazı tipinde kare simge oluşmaması için TL kullanır."""
    return f"{float(value):,.2f} TL"


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
    for column in ["Kolon", "Ic_Tesisat", "Tutar", "Tahsilat", "Ofis_Borcu"]:
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
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=250)
        login_tab, register_tab = st.tabs(["Giriş Yap", "Kayıt Ol"])
        with login_tab:
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
        with register_tab:
            st.caption("Yeni hesaplar Personel rolüyle açılır. Admin, Ayarlar alanından rolü güncelleyebilir.")
            with st.form("register_form", clear_on_submit=True):
                register_name = st.text_input("Ad soyad *", autocomplete="name")
                register_username = st.text_input("Kullanıcı adı *", autocomplete="username")
                register_password = st.text_input("Şifre *", type="password", autocomplete="new-password")
                register_confirm = st.text_input("Şifre tekrar *", type="password", autocomplete="new-password")
                registered = st.form_submit_button("Hesap Oluştur", type="primary", use_container_width=True)
            if registered:
                key = register_username.strip().lower()
                if not register_name.strip() or not key or not register_password:
                    st.error("Ad soyad, kullanıcı adı ve şifre zorunludur.")
                elif len(key) < 3 or not re.fullmatch(r"[a-z0-9._-]+", key):
                    st.error("Kullanıcı adı en az 3 karakter olmalı; yalnızca küçük harf, rakam, nokta, alt çizgi ve tire içerebilir.")
                elif key in st.session_state.users:
                    st.error("Bu kullanıcı adı zaten kullanılıyor.")
                elif len(register_password) < 6:
                    st.error("Şifre en az 6 karakter olmalı.")
                elif register_password != register_confirm:
                    st.error("Şifreler eşleşmiyor.")
                else:
                    st.session_state.users[key] = {"password": register_password, "role": "personel", "name": register_name.strip()}
                    st.success("Hesabınız oluşturuldu. Giriş Yap sekmesinden giriş yapabilirsiniz.")


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
    logo_col, top_left, top_right = st.columns([1, 5, 1])
    with logo_col:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=95)
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


def apply_theme(theme: str) -> None:
    """Koyu ve açık arayüz için dashboard renklerini tek noktadan uygular."""
    is_dark = theme == "Koyu"
    bg = "#080f20" if is_dark else "#f5f7fb"
    panel = "#0d1629" if is_dark else "#ffffff"
    panel_soft = "#111d35" if is_dark else "#eef2f7"
    text = "#f7f9ff" if is_dark else "#14213d"
    muted = "#90a0bb" if is_dark else "#64748b"
    border = "#1b2a46" if is_dark else "#dde5ef"
    input_bg = "#121d32" if is_dark else "#f1f4f8"
    st.markdown(f"""
        <style>
        .stApp {{background: {bg}; color: {text}; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;}}
        [data-testid="stSidebar"] {{background: {panel}; border-right: 1px solid {border};}}
        [data-testid="stSidebar"] * {{color: {text};}}
        .block-container {{padding-top: .8rem; max-width: 1500px;}}
        [data-testid="stMetric"] {{background: {panel}; border: 1px solid {border}; border-radius: 12px; padding: .8rem 1rem; box-shadow: 0 4px 14px rgba(16,24,40,.04);}}
        [data-testid="stMetricLabel"] p, [data-testid="stCaptionContainer"], .stCaption {{color: {muted} !important;}}
        [data-testid="stMetricValue"] {{color: {text};}}
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, textarea {{background: {input_bg} !important; color: {text} !important; border-color: {border} !important;}}
        .stTextInput input, .stNumberInput input {{color: {text} !important;}}
        [data-testid="stDataFrame"] {{border: 1px solid {border}; border-radius: 14px; overflow: hidden;}}
        [data-testid="stForm"] {{border: 1px solid {border}; background: {panel}; border-radius: 14px; padding: 1rem 1.2rem;}}
        [data-testid="stTabs"] [role="tab"] {{color: {muted};}}
        [data-testid="stTabs"] [role="tab"] {{font-weight: 650; font-size: .9rem; padding: .55rem .7rem;}}
        [data-testid="stTabs"] [aria-selected="true"] {{color: #e38100;}}
        [data-testid="stTabs"] [data-baseweb="tab-border"] {{background: {border};}}
        .stButton > button, .stDownloadButton > button {{border-radius: 9px; font-weight: 650;}}
        hr {{border-color: {border} !important; margin: 1rem 0 !important;}}
        .dashboard-title {{font-size: 1.35rem; font-weight: 800; color: {text}; margin: 0; letter-spacing: -.02em;}}
        .dashboard-subtitle {{color: {muted}; font-size: .83rem; margin-top: .15rem;}}
        .clock-box {{background: {panel}; border: 1px solid {border}; border-radius: 10px; padding: .5rem .7rem; text-align: center; color: {text}; font-weight: 700;}}
        </style>
    """, unsafe_allow_html=True)


def master_options() -> list[str]:
    return [master["name"] for master in st.session_state.ustalar] or ["Usta atanmamış"]


def get_master(name: str) -> dict | None:
    return next((master for master in st.session_state.ustalar if master["name"] == name), None)


@st.cache_data(show_spinner=False)
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
            str(len(records)), pdf_money(total_revenue), pdf_money(total_collection),
            pdf_money((total_revenue - total_collection)), str(int(records["Kolon"].sum())),
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
            pdf_money(row["Tutar"]), pdf_money(row["Tahsilat"]),
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
    # Uygulama boş başlar; proje, ciro, tahsilat ve usta kayıtlarını ofis ekler.
    st.session_state.projeler = []

if "users" not in st.session_state:
    st.session_state.users = DEFAULT_USERS.copy()
if "ustalar" not in st.session_state:
    st.session_state.ustalar = DEFAULT_USTALAR.copy()
# Bu sürüme geçildiğinde önceki örnek verileri bir kez temizler.
# Sonraki sayfa yenilemelerinde kullanıcının eklediği kayıtlar korunur.
if "clean_start_v1" not in st.session_state:
    st.session_state.projeler = []
    st.session_state.ustalar = []
    st.session_state.clean_start_v1 = True
# Eski sürümde yalnızca ad olarak kaydedilmiş ustaları yeni bilgi yapısına dönüştürür.
st.session_state.ustalar = [
    master if isinstance(master, dict) else {"name": str(master), "number": "", "phone": ""}
    for master in st.session_state.ustalar
]
if "theme" not in st.session_state:
    st.session_state.theme = "Aydınlık"
if "tv_mode" not in st.session_state:
    st.session_state.tv_mode = False

if "current_user" not in st.session_state:
    render_login()
    st.stop()

current_user = st.session_state.current_user
current_role = current_user["role"]
apply_theme(st.session_state.theme)

if st.session_state.tv_mode:
    render_tv_dashboard()
    st.stop()

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)
st.sidebar.markdown("### Ofis Takip Paneli")
st.sidebar.caption("Güneş Doğalgaz & Mühendislik")
st.sidebar.markdown("---")
selected_theme = st.sidebar.selectbox("🎨 Görünüm", ["Koyu", "Aydınlık"], index=0 if st.session_state.theme == "Koyu" else 1)
if selected_theme != st.session_state.theme:
    st.session_state.theme = selected_theme
    st.rerun()
st.sidebar.success(f"{current_user['name']}\n\nRol: {ROLE_LABELS[current_role]}")
if st.sidebar.button("📺 TV Modunu Aç", use_container_width=True):
    st.session_state.tv_mode = True
    st.rerun()
if st.sidebar.button("↪ Çıkış Yap", use_container_width=True):
    del st.session_state.current_user
    st.rerun()
st.sidebar.markdown("---")
st.sidebar.info("Ciro, tahsilat, kalan alacak ve usta performansını tek ekrandan takip edin.")

header_logo, header_left, header_clock = st.columns([1, 7, 1])
with header_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=82)
with header_left:
    st.markdown('<p class="dashboard-title">☀️ Güneş Doğalgaz | Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="dashboard-subtitle">{date.today().strftime("%B %Y")} · {current_user["name"]} ({ROLE_LABELS[current_role]})</p>', unsafe_allow_html=True)
with header_clock:
    st.markdown(f'<div class="clock-box">🕒 {datetime.now().strftime("%H:%M")}</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ Yeni Proje & İş Kaydı", "🔥 Finans & Performans", "👷 Usta Rehberi & PDF",
    "📋 Merkezi İş Takip", "⚙️ Ayarlar",
])

with tab1:
    df_dashboard = get_dataframe()
    dashboard_month = available_months(df_dashboard)[0]
    dashboard_current = df_dashboard[df_dashboard["Ay"] == dashboard_month] if not df_dashboard.empty else pd.DataFrame(columns=COLUMNS)
    total_debt = df_dashboard["Ofis_Borcu"].sum() if not df_dashboard.empty else 0
    total_receivable = df_dashboard["Kalan_Alacak"].sum() if not df_dashboard.empty else 0
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("🗂️ Toplam Kayıt", f"{len(df_dashboard)}", help="Sistemdeki tüm proje kayıtları")
    d2.metric("👷 Kayıtlı Usta", f"{len(st.session_state.ustalar)}", help="Ayarlar ekranından eklediğiniz ustalar")
    d3.metric("📉 Toplam Borç", tr_money(total_debt), help="Kaydedilmiş ofis borcu ve gider toplamı")
    d4.metric("🏦 Toplam Ofis Alacağı", tr_money(total_receivable), help="Toplam proje bedeli eksi tahsil edilen tutar")
    st.markdown("---")
    st.subheader("📝 Yeni Proje / Kayıt Ekle")
    with st.form("new_project", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            is_tarihi = st.date_input("📅 Proje / kayıt tarihi", value=date.today())
            musteri = st.text_input("Müşteri adı *")
            proje = st.text_input("Proje içeriği / iş adı *")
            gelis_yolu = st.selectbox("Proje geliş yolu", ["WhatsApp", "Telefon", "Referans", "Sosyal Medya", "Diğer"])
            usta = st.selectbox("Atanan usta", master_options())
        with c2:
            tutar = st.number_input("💰 Proje toplam bedeli (TL)", min_value=0.0, step=1000.0, value=5000.0)
            tahsilat = st.number_input("Alınan kapora / ödeme (TL)", min_value=0.0, max_value=float(tutar), step=1000.0, value=0.0)
            ofis_borcu = st.number_input("Ofis borcu / gideri (TL)", min_value=0.0, step=500.0, value=0.0)
            odeme_yontemi = st.selectbox("Ödeme yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet", "Diğer"])
            durum = st.selectbox("İş durumu", ["Devam Ediyor", "Tamamlandı", "Beklemede"])
        with c3:
            sayac_seri_no = st.text_input("Doğalgaz sayaç seri no")
            regulator = st.selectbox("Regülatör durumu", ["Gerekmiyor", "Gerekli", "Takıldı", "Beklemede"])
            kolon = st.number_input("🏢 Kolon sayısı", min_value=0, step=1, value=0)
            ic_tesisat = st.number_input("🔥 İç tesisat sayısı", min_value=0, step=1, value=0)
            diger_islemler = st.multiselect("Diğer işlemler", ["Kombi montaj", "Proje çizimi", "Keşif", "Radyatör", "Menfez", "Baca", "Sayaç başvurusu"])
            surec_adimi = st.selectbox("Armadaş süreç adımı", ["Proje çizim aşamasında", "Onay bekliyor", "Randevu bekliyor", "Gaz açım bekliyor", "Tamamlandı"])
            notlar = st.text_area("Eksik / red nedeni / notlar")
        submitted = st.form_submit_button("Kaydı Ekle", type="primary")
    if submitted:
        if not proje.strip() or not musteri.strip():
            st.warning("Proje adı ve müşteri bilgisi zorunludur.")
        else:
            st.session_state.projeler.append({
                "Tarih": str(is_tarihi), "Ay": is_tarihi.strftime("%Y-%m"), "Usta": usta,
                "Proje": proje.strip(), "Müşteri": musteri.strip(), "Kolon": kolon,
                "Ic_Tesisat": ic_tesisat, "Durum": durum, "Tutar": tutar, "Tahsilat": tahsilat,
                "Odeme_Yontemi": odeme_yontemi, "Sayac_Seri_No": sayac_seri_no,
                "Regulator_Durumu": regulator, "Proje_Gelis_Yolu": gelis_yolu,
                "Diger_Islemler": ", ".join(diger_islemler), "Surec_Adimi": surec_adimi,
                "Notlar": notlar.strip(), "Ofis_Borcu": ofis_borcu,
            })
            st.success(f"{proje} projesi kaydedildi.")

    st.markdown("---")
    st.subheader("🕘 Son Kayıtlar")
    overview = get_dataframe()
    if overview.empty:
        st.info("Henüz kayıtlı proje yok.")
    else:
        st.dataframe(
            overview[["Tarih", "Müşteri", "Proje", "Usta", "Durum", "Tutar", "Tahsilat", "Ofis_Borcu", "Kalan_Alacak", "Odeme_Yontemi", "Sayac_Seri_No", "Regulator_Durumu", "Notlar"]],
            column_config={
                "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                "Ic_Tesisat": "İç Tesisat",
                "Tutar": st.column_config.NumberColumn("Proje Bedeli", format="%.2f ₺"),
                "Tahsilat": st.column_config.NumberColumn("Tahsilat", format="%.2f ₺"),
                "Ofis_Borcu": st.column_config.NumberColumn("Ofis Borcu", format="%.2f ₺"),
                "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
                "Odeme_Yontemi": "Ödeme Tipi", "Sayac_Seri_No": "Sayaç Seri No",
                "Regulator_Durumu": "Regülatör",
            }, hide_index=True, use_container_width=True,
        )

with tab2:
    st.subheader("📊 Mali Durum ve Usta Performans Analizi")
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
    k1.metric("💰 Toplam Ciro", tr_money(revenue), delta=calculate_change(revenue, prev_revenue), delta_color="normal", help=f"{last_month} cirosuna göre değişim")
    k2.metric("✅ Toplam Tahsil Edilen", tr_money(collection))
    k3.metric("⏳ Kalan Ofis Alacağı", tr_money(receivable))
    k4.metric("🗂️ Toplam Proje", f"{len(current)} adet")

    st.markdown("---")
    st.subheader(f"👷 {selected_month} Usta İş Dağılımı")
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
            st.markdown("##### 📊 Kolon ve iç tesisat grafiği")
            st.bar_chart(master_summary.set_index("Usta")[["Kolon Sayısı", "İç Tesisat Sayısı"]], color=["#167D9A", "#F4A261"])
            st.markdown("##### 💵 Ustaların ürettiği ciro")
            st.bar_chart(master_summary.set_index("Usta")[["Ürettiği Ciro"]], color="#2A9D8F")
        with right:
            st.markdown("##### 📋 Usta bilgi ve performans tablosu")
            st.dataframe(master_summary, column_config={
                "Ürettiği Ciro": st.column_config.NumberColumn(format="%.2f ₺"),
                "Tahsilat": st.column_config.NumberColumn(format="%.2f ₺"),
                "Kalan Alacak": st.column_config.NumberColumn(format="%.2f ₺"),
            }, hide_index=True, use_container_width=True)

with tab3:
    st.subheader("📄 Usta Bazlı Proje Raporu")
    df = get_dataframe()
    months = available_months(df)
    a, b = st.columns(2)
    with a:
        selected_master = st.selectbox("Usta seçin", master_options())
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
        st.markdown("##### 🧰 Yaptığı projeler")
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
    st.subheader("📋 Merkezi İş Takip Ekranı")
    st.caption("Müşteri, usta, proje veya sayaç seri no ile arayın; tüm kayıtları tek ekranda inceleyin.")
    central_df = get_dataframe()
    central_search = st.text_input("🔎 Kayıtlarda ara", placeholder="Müşteri, usta, proje veya sayaç seri no")
    if not central_df.empty:
        if central_search.strip():
            text_columns = ["Müşteri", "Usta", "Proje", "Sayac_Seri_No", "Durum"]
            match = pd.Series(False, index=central_df.index)
            for column in text_columns:
                match |= central_df[column].fillna("").astype(str).str.contains(central_search.strip(), case=False, na=False)
            central_df = central_df[match]
        st.dataframe(central_df[["Tarih", "Müşteri", "Proje", "Usta", "Surec_Adimi", "Tutar", "Tahsilat", "Kalan_Alacak", "Odeme_Yontemi", "Sayac_Seri_No", "Regulator_Durumu", "Notlar"]], hide_index=True, use_container_width=True, column_config={
            "Tarih": st.column_config.DateColumn("Kayıt Tarihi", format="DD.MM.YYYY"),
            "Surec_Adimi": "Armadaş Durumu", "Odeme_Yontemi": "Ödeme Tipi", "Sayac_Seri_No": "Sayaç Seri No", "Regulator_Durumu": "Regülatör",
            "Tutar": st.column_config.NumberColumn("Toplam Bedel", format="%.2f ₺"),
            "Tahsilat": st.column_config.NumberColumn("Alınan Ödeme", format="%.2f ₺"),
            "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
        })
    else:
        st.info("Henüz görüntülenecek kayıt bulunmuyor.")
    st.markdown("---")
    if not can_manage_records(current_role):
        st.warning("Kayıt düzenleme ve silme sadece Admin, Yönetici ve Yönetici Yardımcısı rollerine açıktır.")
    else:
        st.subheader("✏️ Kayıt Düzenleme ve Silme")
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
                    edit_masters = master_options()
                    edit_master = st.selectbox("Atanan usta", edit_masters, index=edit_masters.index(record["Usta"]) if record["Usta"] in edit_masters else 0)
                with e2:
                    statuses = ["Devam Ediyor", "Tamamlandı", "Beklemede"]
                    edit_status = st.selectbox("Durum", statuses, index=statuses.index(record["Durum"]) if record["Durum"] in statuses else 0)
                    edit_column = st.number_input("Kolon", min_value=0, step=1, value=int(record["Kolon"]))
                    edit_installation = st.number_input("İç tesisat", min_value=0, step=1, value=int(record["Ic_Tesisat"]))
                    edit_amount = st.number_input("Proje bedeli (TL)", min_value=0.0, value=float(record["Tutar"]), step=1000.0)
                    edit_collection = st.number_input("Tahsilat (TL)", min_value=0.0, max_value=float(edit_amount), value=min(float(record.get("Tahsilat", 0)), float(edit_amount)), step=1000.0)
                    edit_debt = st.number_input("Ofis borcu / gideri (TL)", min_value=0.0, value=float(record.get("Ofis_Borcu", 0) or 0), step=500.0)
                save = st.form_submit_button("Değişiklikleri Kaydet", type="primary")
            if save:
                updated_record = record.copy()
                updated_record.update({"Tarih": str(edit_date), "Ay": edit_date.strftime("%Y-%m"), "Usta": edit_master, "Proje": edit_project, "Müşteri": edit_customer, "Kolon": edit_column, "Ic_Tesisat": edit_installation, "Durum": edit_status, "Tutar": edit_amount, "Tahsilat": edit_collection, "Ofis_Borcu": edit_debt})
                st.session_state.projeler[selected_index] = updated_record
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

with tab5:
    st.subheader("⚙️ Ayarlar ve Yönetim")
    manager_roles = {"admin", "yonetici", "yonetici_yardimcisi"}
    if current_role not in manager_roles:
        st.warning("Bu alan yalnızca yönetim rollerine açıktır.")
    else:
        st.markdown("#### 🪪 Usta Rehberi ve Performans Kartı")
        if st.session_state.ustalar:
            guide_master_name = st.selectbox("Detayını görmek istediğiniz usta", master_options(), key="master_guide")
            guide_master = get_master(guide_master_name)
            guide_df = get_dataframe()
            guide_jobs = guide_df[guide_df["Usta"] == guide_master_name] if not guide_df.empty else pd.DataFrame(columns=COLUMNS)
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Usta Numarası", guide_master["number"] or "—")
            g2.metric("Telefon", guide_master["phone"] or "—")
            g3.metric("Ürettiği Toplam Ciro", tr_money(guide_jobs["Tutar"].sum() if not guide_jobs.empty else 0))
            g4.metric("Kalan Toplam Alacak", tr_money(guide_jobs["Kalan_Alacak"].sum() if not guide_jobs.empty else 0))
            if not guide_jobs.empty:
                st.dataframe(guide_jobs[["Tarih", "Müşteri", "Proje", "Durum", "Kolon", "Ic_Tesisat", "Tutar", "Kalan_Alacak"]], hide_index=True, use_container_width=True, column_config={
                    "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                    "Ic_Tesisat": "İç Tesisat", "Tutar": st.column_config.NumberColumn("Ciro", format="%.2f ₺"),
                    "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
                })
            else:
                st.caption("Bu ustaya henüz proje atanmamış.")
        else:
            st.info("Performans kartını görmek için önce bir usta ekleyin.")
        st.markdown("---")
        st.markdown("#### 👷 Usta Yönetimi")
        add_col, list_col = st.columns([1, 1.4])
        with add_col:
            with st.form("add_master", clear_on_submit=True):
                new_master = st.text_input("Yeni usta adı")
                new_master_number = st.text_input("Usta numarası", placeholder="Örn: U-001")
                new_master_phone = st.text_input("Telefon numarası", placeholder="Örn: 05XX XXX XX XX")
                add_master = st.form_submit_button("Usta Ekle", type="primary")
            if add_master:
                master_name = new_master.strip().upper()
                if not master_name:
                    st.error("Usta adı girin.")
                elif any(master["name"] == master_name for master in st.session_state.ustalar):
                    st.error("Bu usta zaten kayıtlı.")
                elif new_master_number.strip() and any(master["number"] == new_master_number.strip().upper() for master in st.session_state.ustalar):
                    st.error("Bu usta numarası zaten kayıtlı.")
                else:
                    automatic_number = f"U-{len(st.session_state.ustalar) + 1:03d}"
                    st.session_state.ustalar.append({"name": master_name, "number": new_master_number.strip().upper() or automatic_number, "phone": new_master_phone.strip()})
                    st.success(f"{master_name} eklendi.")
                    st.rerun()
        with list_col:
            if not st.session_state.ustalar:
                st.info("Henüz usta eklenmedi. Soldaki formdan ekleyebilirsiniz.")
            else:
                master_names = master_options()
                selected_old_master = st.selectbox("Düzenlenecek / kaldırılacak usta", master_names)
                selected_master_data = get_master(selected_old_master)
                rename_col, number_col, phone_col, delete_col = st.columns([2, 1.15, 1.4, 1])
                renamed_master = rename_col.text_input("Usta adı", value=selected_old_master, key="rename_master")
                edited_master_number = number_col.text_input("Usta no", value=selected_master_data["number"], key="edit_master_no")
                edited_master_phone = phone_col.text_input("Telefon", value=selected_master_data["phone"], key="edit_master_phone")
                if rename_col.button("Ustayı Güncelle"):
                    clean_name = renamed_master.strip().upper()
                    if not clean_name:
                        st.error("Usta adı boş olamaz.")
                    elif clean_name != selected_old_master and clean_name in master_names:
                        st.error("Bu isimde başka bir usta zaten var.")
                    elif edited_master_number.strip() and any(master["number"] == edited_master_number.strip().upper() and master["name"] != selected_old_master for master in st.session_state.ustalar):
                        st.error("Bu usta numarası başka bir ustada kullanılıyor.")
                    else:
                        selected_master_data.update({"name": clean_name, "number": edited_master_number.strip().upper(), "phone": edited_master_phone.strip()})
                        for project in st.session_state.projeler:
                            if project.get("Usta") == selected_old_master:
                                project["Usta"] = clean_name
                        st.success("Usta bilgileri ve ilgili eski kayıtlar güncellendi.")
                        st.rerun()
                if delete_col.button("Ustayı Kaldır", type="secondary"):
                    st.session_state.ustalar.remove(selected_master_data)
                    for project in st.session_state.projeler:
                        if project.get("Usta") == selected_old_master:
                            project["Usta"] = "Usta atanmamış"
                    st.warning("Usta kaldırıldı; eski proje kayıtları 'Usta atanmamış' olarak güncellendi.")
                    st.rerun()
                st.caption(f"Kayıtlı usta sayısı: {len(st.session_state.ustalar)}")

        if current_role == "admin":
            st.markdown("---")
            st.markdown("#### 👤 Kullanıcı Yönetimi")
            user_keys = list(st.session_state.users.keys())
            selected_user_key = st.selectbox("Düzenlenecek / kaldırılacak kullanıcı", user_keys, format_func=lambda key: f"{st.session_state.users[key]['name']} ({key})")
            selected_user = st.session_state.users[selected_user_key]
            with st.form("edit_user"):
                uc1, uc2, uc3 = st.columns(3)
                edited_name = uc1.text_input("Ad soyad", value=selected_user["name"])
                edited_role = uc2.selectbox("Rol", list(ROLE_LABELS), index=list(ROLE_LABELS).index(selected_user["role"]), format_func=lambda role: ROLE_LABELS[role])
                edited_password = uc3.text_input("Yeni şifre (değişmeyecekse boş bırakın)", type="password")
                update_user = st.form_submit_button("Kullanıcıyı Güncelle", type="primary")
            if update_user:
                if not edited_name.strip():
                    st.error("Ad soyad boş olamaz.")
                elif edited_password and len(edited_password) < 6:
                    st.error("Yeni şifre en az 6 karakter olmalı.")
                else:
                    st.session_state.users[selected_user_key]["name"] = edited_name.strip()
                    st.session_state.users[selected_user_key]["role"] = edited_role
                    if edited_password:
                        st.session_state.users[selected_user_key]["password"] = edited_password
                    if selected_user_key == current_user["username"]:
                        st.session_state.current_user = {"username": selected_user_key, **st.session_state.users[selected_user_key]}
                    st.success("Kullanıcı güncellendi.")
                    st.rerun()
            if selected_user_key != current_user["username"]:
                if st.button("Seçili kullanıcıyı kaldır", type="secondary"):
                    removed_name = st.session_state.users.pop(selected_user_key)["name"]
                    st.warning(f"{removed_name} kullanıcısı kaldırıldı.")
                    st.rerun()
            else:
                st.caption("Kendi açık oturumunuzu bu ekrandan kaldıramazsınız.")
