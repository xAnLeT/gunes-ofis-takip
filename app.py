import io
import json
import re
import secrets
import sqlite3
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


st.set_page_config(page_title="Güneş Doğalgaz | Ofis Takip", page_icon="☀️", layout="wide")

LOGO_PATH = Path(__file__).with_name("gunes_muhendislik_logo.jpg")
DATABASE_PATH = Path(__file__).with_name("ofis_takip.sqlite3")
ROLES = {
    "admin": "Admin",
    "yonetici": "Yönetici",
    "yonetici_yardimcisi": "Yönetici Yardımcısı",
    "personel": "Personel",
}
DEFAULT_USERS = {
    "admin": {"name": "Sistem Yöneticisi", "password": "admin123", "role": "admin"},
    "yonetici": {"name": "Ofis Yöneticisi", "password": "yonetici123", "role": "yonetici"},
    "yardimci": {"name": "Yönetici Yardımcısı", "password": "yardimci123", "role": "yonetici_yardimcisi"},
    "personel": {"name": "Ofis Personeli", "password": "personel123", "role": "personel"},
}
DEFAULT_MASTERS = [
    {"name": "GÜNEŞ DOĞALGAZ GNS", "number": "U-001", "phone": ""},
    {"name": "MARTES HİLMİ NOKAY", "number": "U-002", "phone": ""},
    {"name": "MEHMET BEKİROĞLU", "number": "U-003", "phone": ""},
    {"name": "MEHMET YİĞİT", "number": "U-004", "phone": ""},
    {"name": "MUHAMMET SÜT", "number": "U-005", "phone": ""},
    {"name": "MUSTAFA GÜL", "number": "U-006", "phone": ""},
    {"name": "SURİYELİ MUHAMMET", "number": "U-007", "phone": ""},
    {"name": "VATAN SİNAN", "number": "U-008", "phone": ""},
]
ARMADAS_STEPS = [
    # Armadaş ekranındaki resmi sıralama
    "Proje Çizim Aşamasında",
    "Armadaş Dijital Onay Bekliyor",
    "Armadaş Onayladı / Tesisat Aşamasında",
    "Armadaş Randevu Alındı",
    "Armadaş Eksik / Red Aldı",
    "Gaz Açıldı / Müşteriye Teslim Edildi",
]
OTHER_WORKS = [
    "Cihaz Değişimi",
    "Randevu Reddi",
]
PROJECT_COLUMNS = [
    "Tarih", "Ay", "Müşteri", "Proje", "Usta", "Durum", "Tutar", "Tahsilat",
    "Ofis_Borcu", "Odeme_Yontemi", "Sayac_Seri_No", "Regulator_Durumu",
    "Proje_Gelis_Yolu", "Kolon", "Ic_Tesisat", "Diger_Islemler", "Surec_Adimi", "Notlar",
]


def money(value: float) -> str:
    return f"{float(value):,.2f} ₺"


def pdf_money(value: float) -> str:
    return f"{float(value):,.2f} TL"


def ascii_text(value: object) -> str:
    replacement = str.maketrans({"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ü": "u", "Ü": "U", "ö": "o", "Ö": "O", "ç": "c", "Ç": "C"})
    return unicodedata.normalize("NFKD", str(value).translate(replacement)).encode("ascii", "ignore").decode("ascii")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_text(value)).strip("_")


def open_database() -> sqlite3.Connection:
    """Uygulamanın çalıştığı sunucudaki kalıcı kayıt alanını açar."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS application_state (id INTEGER PRIMARY KEY CHECK(id = 1), payload TEXT NOT NULL, saved_at TEXT NOT NULL)")
    return connection


def read_saved_state() -> dict | None:
    with open_database() as connection:
        row = connection.execute("SELECT payload FROM application_state WHERE id = 1").fetchone()
    return json.loads(row[0]) if row else None


def save_state() -> None:
    """Proje, usta ve kullanıcı verilerini Streamlit sunucusuna kaydeder."""
    payload = json.dumps({
        "projects": st.session_state.projects,
        "masters": st.session_state.masters,
        "users": st.session_state.users,
    }, ensure_ascii=False)
    with open_database() as connection:
        connection.execute(
            "INSERT INTO application_state (id, payload, saved_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, saved_at = excluded.saved_at",
            (payload, datetime.now().isoformat(timespec="seconds")),
        )


def normalize_masters(items: list) -> list[dict]:
    return [item.copy() if isinstance(item, dict) else {"name": str(item), "number": "", "phone": ""} for item in items]


def get_df() -> pd.DataFrame:
    df = pd.DataFrame(st.session_state.projects, columns=PROJECT_COLUMNS)
    if df.empty:
        df["Kalan_Alacak"] = pd.Series(dtype="float")
        return df
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
    df["Ay"] = df["Tarih"].dt.strftime("%Y-%m")
    for column in ["Tutar", "Tahsilat", "Ofis_Borcu", "Kolon", "Ic_Tesisat"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    df["Kalan_Alacak"] = (df["Tutar"] - df["Tahsilat"]).clip(lower=0)
    return df


def months(df: pd.DataFrame) -> list[str]:
    values = sorted(df["Ay"].dropna().unique().tolist(), reverse=True) if not df.empty else []
    return values or [date.today().strftime("%Y-%m")]


def previous_month(value: str) -> str:
    return str(pd.Period(value, freq="M") - 1)


def percentage_delta(current: float, previous: float) -> str:
    if previous <= 0:
        return "Yeni dönem" if current else "%0"
    return f"%{((current - previous) / previous) * 100:+.1f}"


def master_names() -> list[str]:
    return [master["name"] for master in st.session_state.masters] or ["Usta atanmamış"]


def find_master(name: str) -> dict | None:
    return next((master for master in st.session_state.masters if master["name"] == name), None)


def is_manager(role: str) -> bool:
    return role in {"admin", "yonetici", "yonetici_yardimcisi"}


def reset_human_check() -> None:
    st.session_state.human_a = secrets.randbelow(8) + 2
    st.session_state.human_b = secrets.randbelow(8) + 2


def human_question() -> str:
    if "human_a" not in st.session_state:
        reset_human_check()
    return f"🛡️ İnsan doğrulaması: {st.session_state.human_a} + {st.session_state.human_b} = ?"


def valid_human(answer: str) -> bool:
    try:
        return int(answer.strip()) == st.session_state.human_a + st.session_state.human_b
    except (ValueError, TypeError):
        return False


def apply_theme(theme: str) -> None:
    dark = theme == "Koyu"
    bg = "#080f20" if dark else "#f5f7fb"
    panel = "#0d1629" if dark else "#ffffff"
    input_bg = "#121d32" if dark else "#f0f3f8"
    text = "#f7f9ff" if dark else "#15233d"
    muted = "#91a0b8" if dark else "#64748b"
    border = "#1d2b46" if dark else "#dbe3ed"
    st.markdown(f"""
    <style>
    .stApp {{background:{bg}; color:{text}; font-family:Inter,ui-sans-serif,system-ui,sans-serif;}}
    [data-testid="stSidebar"] {{background:{panel}; border-right:1px solid {border};}}
    [data-testid="stSidebar"] * {{color:{text};}}
    .block-container {{padding-top:.8rem; max-width:1500px;}}
    [data-testid="stMetric"] {{background:{panel}; border:1px solid {border}; border-radius:12px; padding:.85rem 1rem; box-shadow:0 4px 14px rgba(16,24,40,.04);}}
    [data-testid="stMetricValue"] {{color:{text};}}
    [data-testid="stMetricLabel"] p,[data-testid="stCaptionContainer"],.stCaption {{color:{muted}!important;}}
    [data-testid="stForm"] {{background:{panel}; border:1px solid {border}; border-radius:14px; padding:1rem 1.2rem;}}
    [data-testid="stDataFrame"] {{border:1px solid {border}; border-radius:12px; overflow:hidden;}}
    div[data-baseweb="input"] > div,div[data-baseweb="select"] > div,textarea {{background:{input_bg}!important; color:{text}!important; border-color:{border}!important;}}
    .stTextInput input,.stNumberInput input {{color:{text}!important;}}
    [data-testid="stTabs"] [role="tab"] {{font-size:.88rem;font-weight:700;padding:.55rem .7rem;color:{muted};}}
    [data-testid="stTabs"] [aria-selected="true"] {{color:#df8100;}}
    .brand-title {{font-size:1.35rem;font-weight:850;letter-spacing:-.02em;margin:0;color:{text};}}
    .brand-subtitle {{font-size:.84rem;color:{muted};margin:.12rem 0 0;}}
    .clock {{background:{panel};border:1px solid {border};border-radius:10px;padding:.5rem .65rem;text-align:center;font-weight:750;}}
    .stButton>button,.stDownloadButton>button {{border-radius:9px;font-weight:700;}}
    </style>
    """, unsafe_allow_html=True)


def render_logo(width: int = 105) -> None:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=width)


@st.cache_data(show_spinner=False)
def build_pdf(master: str, month: str, records_json: str) -> bytes:
    records = pd.read_json(io.StringIO(records_json), orient="split")
    records["Tarih"] = pd.to_datetime(records["Tarih"])
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.15 * cm, rightMargin=1.15 * cm, topMargin=1.15 * cm, bottomMargin=1.15 * cm)
    styles = getSampleStyleSheet()
    revenue = records["Tutar"].sum()
    collection = records["Tahsilat"].sum()
    story = [
        Paragraph("GUNES DOGALGAZ & MUHENDISLIK", styles["Title"]),
        Paragraph("USTA PERFORMANS VE PROJE RAPORU", styles["Heading2"]),
        Paragraph(f"Usta: <b>{ascii_text(master)}</b> &nbsp;&nbsp; Donem: <b>{month}</b>", styles["Normal"]),
        Spacer(1, .25 * cm),
    ]
    summary = [["Toplam Proje", "Toplam Ciro", "Tahsilat", "Kalan Alacak", "Kolon", "Ic Tesisat"], [
        str(len(records)), pdf_money(revenue), pdf_money(collection), pdf_money(revenue - collection),
        str(int(records["Kolon"].sum())), str(int(records["Ic_Tesisat"].sum())),
    ]]
    summary_table = Table(summary, colWidths=[2.35 * cm, 3.05 * cm, 3 * cm, 3.15 * cm, 1.7 * cm, 2.2 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#104b5d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#b9c6cc")), ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f3f7f8")),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([summary_table, Spacer(1, .35 * cm), Paragraph("PROJE DETAYLARI", styles["Heading3"])])
    rows = [["Tarih", "Proje / Musteri", "Durum", "Kolon", "Ic Tesisat", "Ciro", "Tahsilat"]]
    for _, row in records.sort_values("Tarih").iterrows():
        rows.append([
            row["Tarih"].strftime("%d.%m.%Y"), f"{ascii_text(row['Proje'])}\n{ascii_text(row['Müşteri'])}",
            ascii_text(row["Durum"]), str(int(row["Kolon"])), str(int(row["Ic_Tesisat"])), pdf_money(row["Tutar"]), pdf_money(row["Tahsilat"]),
        ])
    detail = Table(rows, repeatRows=1, colWidths=[2 * cm, 5.2 * cm, 2.3 * cm, 1.3 * cm, 1.8 * cm, 2.8 * cm, 2.8 * cm])
    detail.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#167d9a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#c7d1d5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafb")]),
    ]))
    story.append(detail)
    document.build(story)
    return buffer.getvalue()


def render_login() -> None:
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    _, middle, _ = st.columns([1, 1.35, 1])
    with middle:
        render_logo(250)
        st.markdown("### Güneş Doğalgaz & Mühendislik")
        st.caption("Kurumsal proje yönetim ve iş takip paneli")
        login_tab, register_tab = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Kullanıcı adı", autocomplete="username")
                password = st.text_input("Şifre", type="password", autocomplete="current-password")
                human = st.text_input(human_question(), placeholder="Sonucu yazın", key="login_human")
                submitted = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            if submitted:
                user = st.session_state.users.get(username.strip().lower())
                if not valid_human(human):
                    st.error("İnsan doğrulaması hatalı.")
                    reset_human_check()
                elif user and user["password"] == password:
                    st.session_state.current_user = {"username": username.strip().lower(), **user}
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
        with register_tab:
            st.caption("Yeni hesaplar Personel rolüyle açılır. Admin, rolü Ayarlar alanından güncelleyebilir.")
            with st.form("register_form", clear_on_submit=True):
                full_name = st.text_input("Ad soyad *")
                new_username = st.text_input("Kullanıcı adı *")
                new_password = st.text_input("Şifre *", type="password")
                password_again = st.text_input("Şifre tekrar *", type="password")
                register_human = st.text_input(human_question(), placeholder="Sonucu yazın", key="register_human")
                create_account = st.form_submit_button("Hesap Oluştur", type="primary", use_container_width=True)
            if create_account:
                key = new_username.strip().lower()
                if not valid_human(register_human):
                    st.error("İnsan doğrulaması hatalı.")
                    reset_human_check()
                elif not full_name.strip() or not key or not new_password:
                    st.error("Ad soyad, kullanıcı adı ve şifre zorunludur.")
                elif not re.fullmatch(r"[a-z0-9._-]{3,}", key):
                    st.error("Kullanıcı adı en az 3 karakter olmalı; küçük harf, rakam, nokta, alt çizgi veya tire kullanın.")
                elif key in st.session_state.users:
                    st.error("Bu kullanıcı adı zaten kullanılıyor.")
                elif len(new_password) < 6:
                    st.error("Şifre en az 6 karakter olmalı.")
                elif new_password != password_again:
                    st.error("Şifreler eşleşmiyor.")
                else:
                    st.session_state.users[key] = {"name": full_name.strip(), "password": new_password, "role": "personel"}
                    save_state()
                    st.success("Hesap oluşturuldu. Giriş yapabilirsiniz.")


def render_tv() -> None:
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stHeader']{display:none}.block-container{max-width:100%;padding:1.5rem 3rem}[data-testid='stMetricValue']{font-size:2.45rem}</style>", unsafe_allow_html=True)
    logo, title, action = st.columns([1, 5, 1])
    with logo:
        render_logo(95)
    with title:
        st.title("☀️ Güneş Doğalgaz | Canlı Ofis Ekranı")
        st.caption(f"Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    with action:
        if st.button("TV Modundan Çık", use_container_width=True):
            st.session_state.tv_mode = False
            st.rerun()
    df = get_df()
    month = months(df)[0]
    current = df[df["Ay"] == month] if not df.empty else df
    revenue = current["Tutar"].sum() if not current.empty else 0
    collection = current["Tahsilat"].sum() if not current.empty else 0
    active = len(current[current["Durum"] == "Devam Ediyor"]) if not current.empty else 0
    a, b, c, d = st.columns(4)
    a.metric(f"{month} Toplam Ciro", money(revenue))
    b.metric("Tahsil Edilen", money(collection))
    c.metric("Kalan Ofis Alacağı", money(revenue - collection))
    d.metric("Devam Eden İş", f"{active} adet")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("📊 Usta Performansı")
        if not current.empty:
            summary = current.groupby("Usta", as_index=False).agg(Ciro=("Tutar", "sum")).sort_values("Ciro", ascending=False)
            st.bar_chart(summary.set_index("Usta"), color="#2a9d8f")
    with right:
        st.subheader("🕘 Açık Projeler")
        open_projects = current[current["Durum"] != "Tamamlandı"] if not current.empty else current
        if open_projects.empty:
            st.success("Gösterilecek açık proje yok.")
        else:
            st.dataframe(open_projects[["Müşteri", "Usta", "Proje", "Durum", "Tutar"]], hide_index=True, use_container_width=True, column_config={"Tutar": st.column_config.NumberColumn("Ciro", format="%.2f ₺")})
    st.caption("Tam ekran kullanım için tarayıcıda F11 tuşuna basın.")


if "storage_loaded" not in st.session_state:
    saved = read_saved_state()
    if saved:
        st.session_state.projects = saved.get("projects", [])
        st.session_state.masters = normalize_masters(saved.get("masters", DEFAULT_MASTERS))
        st.session_state.users = saved.get("users", {key: value.copy() for key, value in DEFAULT_USERS.items()})
    else:
        # İlk kayıt anında varsa eski oturum verisini korur, sonra sunucuya kaydeder.
        current_projects = list(st.session_state.get("projects", []))
        st.session_state.projects = current_projects or list(st.session_state.get("projeler", []))
        st.session_state.masters = normalize_masters(st.session_state.get("masters", DEFAULT_MASTERS))
        for legacy_master in normalize_masters(st.session_state.get("ustalar", [])):
            if legacy_master["name"] and not any(master["name"] == legacy_master["name"] for master in st.session_state.masters):
                st.session_state.masters.append(legacy_master)
        st.session_state.users = st.session_state.get("users", {key: value.copy() for key, value in DEFAULT_USERS.items()})
        save_state()
    st.session_state.storage_loaded = True
if "theme" not in st.session_state:
    st.session_state.theme = "Aydınlık"
if "tv_mode" not in st.session_state:
    st.session_state.tv_mode = False

if "current_user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state.current_user
role = user["role"]
apply_theme(st.session_state.theme)
if st.session_state.tv_mode:
    render_tv()
    st.stop()

with st.sidebar:
    render_logo(180)
    st.markdown("### 💼 Ofis Takip Paneli")
    st.caption("Güneş Doğalgaz & Mühendislik")
    st.markdown("---")
    new_theme = st.selectbox("🎨 Görünüm", ["Aydınlık", "Koyu"], index=0 if st.session_state.theme == "Aydınlık" else 1)
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()
    st.success(f"👤 {user['name']}\n\nRol: {ROLES[role]}")
    if st.button("💾 Verileri Sunucuya Kaydet", use_container_width=True):
        save_state()
        st.success("Veriler site kayıt alanına kaydedildi.")
    if st.button("📺 TV Modunu Aç", use_container_width=True):
        st.session_state.tv_mode = True
        st.rerun()
    if st.button("↪ Çıkış Yap", use_container_width=True):
        del st.session_state.current_user
        st.rerun()
    st.caption("☁️ Otomatik kayıt açık")

head_logo, head_title, head_clock = st.columns([1, 7, 1])
with head_logo:
    render_logo(82)
with head_title:
    st.markdown("<p class='brand-title'>☀️ Güneş Doğalgaz | Dashboard</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='brand-subtitle'>{date.today().strftime('%d.%m.%Y')} · {user['name']} ({ROLES[role]})</p>", unsafe_allow_html=True)
with head_clock:
    st.markdown(f"<div class='clock'>🕒 {datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ Yeni Proje & İş Kaydı", "🔥 Finans & Performans", "👷 Usta Rehberi & PDF", "📋 Merkezi İş Takip", "⚙️ Ayarlar",
])

with tab1:
    df = get_df()
    debt = df["Ofis_Borcu"].sum() if not df.empty else 0
    receivable = df["Kalan_Alacak"].sum() if not df.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🗂️ Toplam Kayıt", len(df))
    k2.metric("👷 Kayıtlı Usta", len(st.session_state.masters))
    k3.metric("📉 Toplam Borç", money(debt))
    k4.metric("🏦 Toplam Ofis Alacağı", money(receivable))
    st.markdown("---")
    st.subheader("📝 Yeni Proje / İş Kaydı")
    with st.form("new_project", clear_on_submit=True):
        left, middle, right = st.columns(3)
        with left:
            st.markdown("##### 📌 Genel Bilgiler")
            project_date = st.date_input("📅 Proje / kayıt tarihi", value=date.today())
            customer = st.text_input("Müşteri adı *")
            project_name = st.text_input("Proje içeriği / iş adı *")
            source = st.selectbox("Proje geliş yolu", ["WhatsApp", "Telefon", "Referans", "Sosyal Medya", "Diğer"])
            assigned_master = st.selectbox("Atanan usta", master_names())
        with middle:
            st.markdown("##### 💰 Finansal Durum")
            amount = st.number_input("Proje toplam bedeli (TL)", min_value=0.0, step=1000.0, value=0.0)
            payment = st.number_input("Alınan kapora / ödeme (TL)", min_value=0.0, max_value=float(amount), step=1000.0, value=0.0)
            payment_method = st.selectbox("Ödeme yöntemi", ["Nakit", "Havale / EFT", "Kredi Kartı", "Çek / Senet", "Ödeme Alınmadı", "Diğer"])
            job_status = st.selectbox("İş durumu", ["Devam Ediyor", "Tamamlandı", "Beklemede"])
        with right:
            st.markdown("##### 📦 Malzeme ve Sayaç Detayları")
            meter_number = st.text_input("Doğalgaz sayaç seri no")
            regulator = st.selectbox("Regülatör durumu", ["Gerekmiyor", "Gerekli", "Takıldı", "Kutuda Var", "Beklemede"])
            columns_count = st.number_input("🏢 Kolon sayısı", min_value=0, step=1, value=0)
            installation_count = st.number_input("🔥 İç tesisat sayısı", min_value=0, step=1, value=0)
            other_works = st.multiselect("⚙️ Diğer işlemler", OTHER_WORKS, placeholder="İşlem seçin")
            armadas_step = st.selectbox("🔄 Armadaş süreç adımı", ARMADAS_STEPS)
            notes = st.text_area("🗒️ Eksik / red nedeni / notlar")
        submit_project = st.form_submit_button("➕ Kaydı Ekle", type="primary")
    if submit_project:
        if not customer.strip() or not project_name.strip():
            st.warning("Müşteri adı ve proje içeriği zorunludur.")
        else:
            st.session_state.projects.append({
                "Tarih": str(project_date), "Ay": project_date.strftime("%Y-%m"), "Müşteri": customer.strip(), "Proje": project_name.strip(),
                "Usta": assigned_master, "Durum": job_status, "Tutar": amount, "Tahsilat": payment, "Ofis_Borcu": 0,
                "Odeme_Yontemi": payment_method, "Sayac_Seri_No": meter_number.strip(), "Regulator_Durumu": regulator,
                "Proje_Gelis_Yolu": source, "Kolon": columns_count, "Ic_Tesisat": installation_count,
                "Diger_Islemler": ", ".join(other_works), "Surec_Adimi": armadas_step, "Notlar": notes.strip(),
            })
            save_state()
            st.success("Proje kaydı eklendi.")
            st.rerun()
    st.markdown("---")
    st.subheader("🕘 Son Kayıtlar")
    df = get_df()
    if df.empty:
        st.info("Henüz kayıt yok. Yukarıdaki formdan ilk projeyi ekleyebilirsiniz.")
    else:
        st.dataframe(df.sort_values("Tarih", ascending=False)[["Tarih", "Müşteri", "Proje", "Usta", "Durum", "Tutar", "Tahsilat", "Kalan_Alacak", "Surec_Adimi"]], hide_index=True, use_container_width=True, column_config={
            "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"), "Surec_Adimi": "Armadaş Durumu",
            "Tutar": st.column_config.NumberColumn("Toplam Bedel", format="%.2f ₺"), "Tahsilat": st.column_config.NumberColumn("Alınan Ödeme", format="%.2f ₺"),
            "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
        })

with tab2:
    st.subheader("📊 Mali Durum ve Usta Performans Analizi")
    df = get_df()
    selected_month = st.selectbox("📅 Rapor dönemi", months(df))
    current = df[df["Ay"] == selected_month].copy() if not df.empty else df
    previous = df[df["Ay"] == previous_month(selected_month)] if not df.empty else df
    revenue = current["Tutar"].sum() if not current.empty else 0
    collection = current["Tahsilat"].sum() if not current.empty else 0
    previous_revenue = previous["Tutar"].sum() if not previous.empty else 0
    a, b, c, d = st.columns(4)
    a.metric("💰 Toplam Ciro", money(revenue), delta=percentage_delta(revenue, previous_revenue))
    b.metric("✅ Tahsil Edilen", money(collection))
    c.metric("⏳ Kalan Ofis Alacağı", money(revenue - collection))
    d.metric("🗂️ Toplam Proje", f"{len(current)} adet")
    st.markdown("---")
    st.subheader(f"👷 {selected_month} Usta İş Dağılımı")
    if current.empty:
        st.info("Bu ay için analiz verisi bulunmuyor.")
    else:
        summary = current.groupby("Usta", as_index=False).agg(**{
            "Toplam İş": ("Proje", "count"), "Kolon Sayısı": ("Kolon", "sum"), "İç Tesisat": ("Ic_Tesisat", "sum"),
            "Ürettiği Ciro": ("Tutar", "sum"), "Tahsilat": ("Tahsilat", "sum"), "Kalan Alacak": ("Kalan_Alacak", "sum"),
        }).sort_values("Ürettiği Ciro", ascending=False)
        chart, table = st.columns([1.15, 1])
        with chart:
            st.markdown("##### 📊 Kolon ve iç tesisat")
            st.bar_chart(summary.set_index("Usta")[["Kolon Sayısı", "İç Tesisat"]], color=["#167d9a", "#f4a261"])
            st.markdown("##### 💵 Usta ciroları")
            st.bar_chart(summary.set_index("Usta")[["Ürettiği Ciro"]], color="#2a9d8f")
        with table:
            st.markdown("##### 📋 Usta performans tablosu")
            st.dataframe(summary, hide_index=True, use_container_width=True, column_config={
                "Ürettiği Ciro": st.column_config.NumberColumn(format="%.2f ₺"), "Tahsilat": st.column_config.NumberColumn(format="%.2f ₺"),
                "Kalan Alacak": st.column_config.NumberColumn(format="%.2f ₺"),
            })

with tab3:
    st.subheader("👷 Usta Rehberi ve PDF Raporu")
    df = get_df()
    selected_master = st.selectbox("Usta seçin", master_names(), key="pdf_master")
    selected_month = st.selectbox("Rapor ayı", months(df), key="pdf_month")
    master_data = find_master(selected_master)
    master_projects = df[(df["Usta"] == selected_master) & (df["Ay"] == selected_month)].copy() if not df.empty else df
    contact, number, phone = st.columns(3)
    contact.metric("👷 Usta", selected_master)
    number.metric("🪪 Usta Numarası", master_data["number"] if master_data else "—")
    phone.metric("📞 Telefon", master_data["phone"] if master_data and master_data["phone"] else "—")
    if master_projects.empty:
        st.info("Bu usta için seçilen ayda proje bulunmuyor.")
    else:
        revenue = master_projects["Tutar"].sum()
        collection = master_projects["Tahsilat"].sum()
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("🗂️ Proje", f"{len(master_projects)} adet")
        p2.metric("💰 Ciro", money(revenue))
        p3.metric("✅ Tahsilat", money(collection))
        p4.metric("🏢 Kolon", int(master_projects["Kolon"].sum()))
        p5.metric("🔥 İç Tesisat", int(master_projects["Ic_Tesisat"].sum()))
        st.markdown("##### 🧰 Yapılan projeler")
        st.dataframe(master_projects[["Tarih", "Müşteri", "Proje", "Durum", "Kolon", "Ic_Tesisat", "Tutar", "Tahsilat", "Kalan_Alacak"]], hide_index=True, use_container_width=True, column_config={
            "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"), "Ic_Tesisat": "İç Tesisat",
            "Tutar": st.column_config.NumberColumn("Ciro", format="%.2f ₺"), "Tahsilat": st.column_config.NumberColumn(format="%.2f ₺"),
            "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
        })
        report_json = master_projects.to_json(orient="split", date_format="iso")
        st.download_button("📄 Usta raporunu PDF indir", data=build_pdf(selected_master, selected_month, report_json), file_name=f"{safe_filename(selected_master)}_{selected_month}_raporu.pdf", mime="application/pdf", type="primary")

with tab4:
    st.subheader("📋 Merkezi İş Takip Ekranı")
    st.caption("Müşteri, usta, proje veya sayaç seri no ile arayın; tüm kayıtları tek ekranda inceleyin.")
    df = get_df()
    query = st.text_input("🔎 Kayıtlarda ara", placeholder="Müşteri, usta, proje veya sayaç seri no")
    shown = df.copy()
    if not df.empty and query.strip():
        found = pd.Series(False, index=df.index)
        for column in ["Müşteri", "Usta", "Proje", "Sayac_Seri_No", "Durum", "Surec_Adimi"]:
            found |= df[column].fillna("").astype(str).str.contains(query.strip(), case=False, na=False)
        shown = df[found]
    if shown.empty:
        st.info("Gösterilecek kayıt bulunmuyor.")
    else:
        st.dataframe(shown[["Tarih", "Müşteri", "Proje", "Usta", "Surec_Adimi", "Tutar", "Tahsilat", "Kalan_Alacak", "Odeme_Yontemi", "Sayac_Seri_No", "Regulator_Durumu", "Notlar"]], hide_index=True, use_container_width=True, column_config={
            "Tarih": st.column_config.DateColumn("Kayıt Tarihi", format="DD.MM.YYYY"), "Surec_Adimi": "Armadaş Durumu", "Odeme_Yontemi": "Ödeme Tipi",
            "Sayac_Seri_No": "Sayaç Seri No", "Regulator_Durumu": "Regülatör", "Tutar": st.column_config.NumberColumn("Toplam Bedel", format="%.2f ₺"),
            "Tahsilat": st.column_config.NumberColumn("Alınan Ödeme", format="%.2f ₺"), "Kalan_Alacak": st.column_config.NumberColumn("Kalan Alacak", format="%.2f ₺"),
        })
    st.markdown("---")
    if not is_manager(role):
        st.warning("✏️ Kayıt düzenleme ve silme, yönetim rollerine açıktır.")
    elif not st.session_state.projects:
        st.info("Düzenlenecek kayıt bulunmuyor.")
    else:
        st.subheader("✏️ Kayıt Düzenleme ve Silme")
        index = st.selectbox("Düzenlenecek kayıt", range(len(st.session_state.projects)), format_func=lambda i: f"{st.session_state.projects[i]['Tarih']} | {st.session_state.projects[i]['Müşteri']} | {st.session_state.projects[i]['Proje']}")
        record = st.session_state.projects[index]
        with st.form("edit_project"):
            e1, e2 = st.columns(2)
            with e1:
                edit_date = st.date_input("Tarih", value=pd.to_datetime(record["Tarih"]).date())
                edit_customer = st.text_input("Müşteri", value=record["Müşteri"])
                edit_project = st.text_input("Proje", value=record["Proje"])
                options = master_names()
                edit_master = st.selectbox("Usta", options, index=options.index(record["Usta"]) if record["Usta"] in options else 0)
            with e2:
                edit_status = st.selectbox("Durum", ["Devam Ediyor", "Tamamlandı", "Beklemede"], index=["Devam Ediyor", "Tamamlandı", "Beklemede"].index(record["Durum"]))
                edit_amount = st.number_input("Proje bedeli", min_value=0.0, value=float(record["Tutar"]), step=1000.0)
                edit_payment = st.number_input("Tahsilat", min_value=0.0, max_value=float(edit_amount), value=min(float(record["Tahsilat"]), float(edit_amount)), step=1000.0)
                edit_debt = st.number_input("Ofis borcu / gideri", min_value=0.0, value=float(record.get("Ofis_Borcu", 0)), step=500.0)
            save = st.form_submit_button("Değişiklikleri Kaydet", type="primary")
        if save:
            record.update({"Tarih": str(edit_date), "Ay": edit_date.strftime("%Y-%m"), "Müşteri": edit_customer.strip(), "Proje": edit_project.strip(), "Usta": edit_master, "Durum": edit_status, "Tutar": edit_amount, "Tahsilat": edit_payment, "Ofis_Borcu": edit_debt})
            save_state()
            st.success("Kayıt güncellendi.")
            st.rerun()
        if role in {"admin", "yonetici"} and st.button("🗑️ Seçili kaydı sil", type="secondary"):
            st.session_state.projects.pop(index)
            save_state()
            st.warning("Kayıt silindi.")
            st.rerun()

with tab5:
    st.subheader("⚙️ Ayarlar ve Yönetim")
    if not is_manager(role):
        st.warning("Bu alan yalnızca yönetim rollerine açıktır.")
    else:
        st.markdown("#### 🪪 Usta Rehberi ve Performans")
        selected = st.selectbox("Detayını görmek istediğiniz usta", master_names(), key="guide_master")
        master = find_master(selected)
        df = get_df()
        master_df = df[df["Usta"] == selected] if not df.empty else df
        a, b, c, d = st.columns(4)
        a.metric("Usta Numarası", master["number"] if master else "—")
        b.metric("Telefon", master["phone"] if master and master["phone"] else "—")
        c.metric("Ürettiği Ciro", money(master_df["Tutar"].sum() if not master_df.empty else 0))
        d.metric("Kalan Alacak", money(master_df["Kalan_Alacak"].sum() if not master_df.empty else 0))
        st.markdown("---")
        st.markdown("#### 👷 Usta Yönetimi")
        add, manage = st.columns([1, 1.4])
        with add:
            with st.form("add_master", clear_on_submit=True):
                master_name = st.text_input("Yeni usta adı")
                master_number = st.text_input("Usta numarası", placeholder="Örn: U-009")
                master_phone = st.text_input("Telefon numarası", placeholder="05XX XXX XX XX")
                add_master = st.form_submit_button("➕ Usta Ekle", type="primary")
            if add_master:
                name = master_name.strip().upper()
                number = master_number.strip().upper() or f"U-{len(st.session_state.masters) + 1:03d}"
                if not name:
                    st.error("Usta adı zorunludur.")
                elif any(item["name"] == name for item in st.session_state.masters):
                    st.error("Bu usta zaten kayıtlı.")
                elif any(item["number"] == number for item in st.session_state.masters):
                    st.error("Bu usta numarası kullanılıyor.")
                else:
                    st.session_state.masters.append({"name": name, "number": number, "phone": master_phone.strip()})
                    save_state()
                    st.success("Usta eklendi.")
                    st.rerun()
        with manage:
            if st.session_state.masters:
                old_name = st.selectbox("Düzenlenecek / kaldırılacak usta", master_names(), key="manage_master")
                item = find_master(old_name)
                m1, m2, m3 = st.columns(3)
                changed_name = m1.text_input("Usta adı", value=item["name"])
                changed_number = m2.text_input("Usta no", value=item["number"])
                changed_phone = m3.text_input("Telefon", value=item["phone"])
                update, remove = st.columns(2)
                if update.button("💾 Ustayı Güncelle"):
                    new_name = changed_name.strip().upper()
                    new_number = changed_number.strip().upper()
                    if not new_name or not new_number:
                        st.error("Usta adı ve numarası zorunludur.")
                    elif any(x["name"] == new_name and x is not item for x in st.session_state.masters) or any(x["number"] == new_number and x is not item for x in st.session_state.masters):
                        st.error("Usta adı veya numarası başka bir ustada kullanılıyor.")
                    else:
                        item.update({"name": new_name, "number": new_number, "phone": changed_phone.strip()})
                        for project in st.session_state.projects:
                            if project["Usta"] == old_name:
                                project["Usta"] = new_name
                        save_state()
                        st.success("Usta bilgileri güncellendi.")
                        st.rerun()
                if remove.button("🗑️ Ustayı Kaldır", type="secondary"):
                    st.session_state.masters.remove(item)
                    for project in st.session_state.projects:
                        if project["Usta"] == old_name:
                            project["Usta"] = "Usta atanmamış"
                    save_state()
                    st.warning("Usta kaldırıldı.")
                    st.rerun()
        if role == "admin":
            st.markdown("---")
            st.markdown("#### 👤 Kullanıcı Yönetimi")
            with st.form("add_user", clear_on_submit=True):
                u1, u2, u3, u4 = st.columns(4)
                add_username = u1.text_input("Kullanıcı adı")
                add_name = u2.text_input("Ad soyad")
                add_password = u3.text_input("İlk şifre", type="password")
                add_role = u4.selectbox("Rol", list(ROLES), format_func=lambda value: ROLES[value])
                add_user = st.form_submit_button("➕ Kullanıcı Ekle")
            if add_user:
                key = add_username.strip().lower()
                if not key or not add_name.strip() or len(add_password) < 6:
                    st.error("Kullanıcı adı, ad soyad ve en az 6 karakterli şifre zorunludur.")
                elif key in st.session_state.users:
                    st.error("Bu kullanıcı adı zaten var.")
                else:
                    st.session_state.users[key] = {"name": add_name.strip(), "password": add_password, "role": add_role}
                    save_state()
                    st.success("Kullanıcı eklendi.")
            user_key = st.selectbox("Düzenlenecek kullanıcı", list(st.session_state.users), format_func=lambda key: f"{st.session_state.users[key]['name']} ({key})")
            edited = st.session_state.users[user_key]
            with st.form("edit_user"):
                x1, x2, x3 = st.columns(3)
                changed_user_name = x1.text_input("Ad soyad", value=edited["name"])
                changed_user_role = x2.selectbox("Rol", list(ROLES), index=list(ROLES).index(edited["role"]), format_func=lambda value: ROLES[value])
                changed_password = x3.text_input("Yeni şifre (boş bırakılabilir)", type="password")
                save_user = st.form_submit_button("💾 Kullanıcıyı Güncelle", type="primary")
            if save_user:
                if not changed_user_name.strip() or (changed_password and len(changed_password) < 6):
                    st.error("Ad soyad zorunlu; yeni şifre en az 6 karakter olmalı.")
                else:
                    edited.update({"name": changed_user_name.strip(), "role": changed_user_role})
                    if changed_password:
                        edited["password"] = changed_password
                    if user_key == user["username"]:
                        st.session_state.current_user = {"username": user_key, **edited}
                    save_state()
                    st.success("Kullanıcı güncellendi.")
                    st.rerun()
            if user_key != user["username"] and st.button("🗑️ Seçili kullanıcıyı kaldır", type="secondary"):
                st.session_state.users.pop(user_key)
                save_state()
                st.warning("Kullanıcı kaldırıldı.")
                st.rerun()
