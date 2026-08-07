import io
import json
import html
import re
import secrets
import sqlite3
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


st.set_page_config(page_title="Güneş Doğalgaz | Ofis Takip", page_icon="☀️", layout="wide")

LOGO_PATH = Path(__file__).with_name("gunes_muhendislik_logo.jpg")
DATABASE_PATH = Path(__file__).with_name("ofis_takip.sqlite3")
TURKEY_TIMEZONE = ZoneInfo("Europe/Istanbul")
ROLES = {
    "admin": "Admin",
    "yonetici": "Yönetici",
    "yonetici_yardimcisi": "Yönetici Yardımcısı",
    "personel": "Personel",
}
PERMISSION_LABELS = {
    "project_edit": "Proje kayıtlarını düzenleme",
    "project_delete": "Proje kayıtlarını silme",
    "masters_manage": "Usta rehberini yönetme",
    "users_manage": "Kullanıcı ve izin yönetimi",
}
ROLE_PERMISSIONS = {
    "admin": set(PERMISSION_LABELS),
    "yonetici": {"project_edit", "project_delete", "masters_manage"},
    "yonetici_yardimcisi": {"project_edit", "masters_manage"},
    "personel": set(),
}
DEFAULT_USERS = {
    "admin": {"name": "Sistem Yöneticisi", "password": "admin123", "role": "admin"},
    "yonetici": {"name": "Ofis Yöneticisi", "password": "yonetici123", "role": "yonetici"},
    "yardimci": {"name": "Yönetici Yardımcısı", "password": "yardimci123", "role": "yonetici_yardimcisi"},
    "personel": {"name": "Ofis Personeli", "password": "personel123", "role": "personel"},
}
# Usta listesi ve telefonlar uygulama kodunda tutulmaz; site veritabanından yönetilir.
DEFAULT_MASTERS: list[dict] = []
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


def turkey_now() -> datetime:
    """Ekrandaki tarih ve saat için sunucudan bağımsız Türkiye saatini döndürür."""
    return datetime.now(TURKEY_TIMEZONE)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_tcmb_rates() -> dict[str, float]:
    """TCMB günlük XML verisinden USD ve EUR satış kurlarını getirir."""
    try:
        with urllib.request.urlopen("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=6) as response:
            root = ET.fromstring(response.read())
        rates = {}
        for code in ("USD", "EUR"):
            currency = root.find(f".//Currency[@CurrencyCode='{code}']")
            selling = currency.findtext("ForexSelling") if currency is not None else None
            if selling:
                rates[code] = float(selling.replace(",", "."))
        return rates
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_quotes() -> dict[str, float]:
    """Ücretsiz kaynaklardan USD, EUR ve gram altın TL değerlerini getirir."""
    quotes = fetch_tcmb_rates()
    try:
        request = urllib.request.Request(
            "https://api.gold-api.com/price/XAU",
            headers={"User-Agent": "GunesOfisTakip/1.0"},
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            gold_data = json.loads(response.read().decode("utf-8"))
        # Kaynak XAU spot fiyatını USD/troy ons olarak verir. 1 troy ons = 31,1034768 gramdır.
        ounce_usd = float(gold_data.get("price") or gold_data.get("ask") or gold_data.get("bid") or 0)
        if ounce_usd > 0 and quotes.get("USD"):
            quotes["GRAM_ALTIN"] = (ounce_usd * quotes["USD"]) / 31.1034768
    except Exception:
        pass
    return quotes


def market_change(key: str, value: float | None) -> tuple[str, str]:
    """Bu tarayıcı oturumunda son yenilemeden itibaren fiyat değişimini gösterir."""
    if value is None:
        return "Veri bekleniyor", "#94a3b8"
    state_key = f"market_previous_{key}"
    previous = st.session_state.get(state_key)
    st.session_state[state_key] = value
    if previous is None:
        return "İlk değer", "#94a3b8"
    difference = value - float(previous)
    if abs(difference) < 0.00001:
        return "• Değişmedi", "#94a3b8"
    arrow, colour = ("▲", "#22c55e") if difference > 0 else ("▼", "#ef4444")
    return f"{arrow} {abs(difference):,.4f} TL", colour


def _number_or_none(value: object) -> float | None:
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_kahramanmaras_weather() -> dict[str, object]:
    """Kahramanmaraş için güncel koşulları ve günün sıcaklık aralığını getirir."""
    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=37.5858&longitude=36.9371"
        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min&timezone=Europe%2FIstanbul"
    )
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
        current = payload.get("current", {})
        daily = payload.get("daily", {})
        return {
            "temperature": current.get("temperature_2m"),
            "apparent": current.get("apparent_temperature"),
            "weather_code": current.get("weather_code"),
            "wind": current.get("wind_speed_10m"),
            "minimum": (daily.get("temperature_2m_min") or [None])[0],
            "maximum": (daily.get("temperature_2m_max") or [None])[0],
        }
    except Exception:
        return {}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_kahramanmaras_fuel_prices() -> dict[str, float]:
    """Açık akaryakıt verisinden Kahramanmaraş litre fiyatlarını getirir."""
    try:
        with urllib.request.urlopen("https://www.hasanadiguzel.com.tr/api/akaryakit/sehir=kahramanmaras", timeout=7) as response:
            payload = json.loads(response.read().decode("utf-8"))
        stations = payload.get("data", [])
        row = stations[0] if stations else {}
        normalized = {ascii_text(key).lower(): value for key, value in row.items()}

        def find_value(*tokens: str) -> float | None:
            for key, value in normalized.items():
                if all(token in key for token in tokens):
                    parsed = _number_or_none(value)
                    if parsed is not None:
                        return parsed
            return None

        values = {
            "Benzin": find_value("kursunsuz", "95"),
            "Motorin": find_value("motorin", "eurodiesel"),
            "LPG": find_value("otogaz"),
        }
        return {key: value for key, value in values.items() if value is not None}
    except Exception:
        return {}


def weather_label(code: object) -> str:
    labels = {
        0: "Açık", 1: "Az bulutlu", 2: "Parçalı bulutlu", 3: "Bulutlu",
        45: "Sisli", 48: "Kırağı sisli", 51: "Çisenti", 53: "Çisenti", 55: "Çisenti",
        61: "Yağmurlu", 63: "Yağmurlu", 65: "Kuvvetli yağmur", 71: "Karlı", 73: "Karlı",
        75: "Yoğun kar", 80: "Sağanak", 81: "Sağanak", 82: "Kuvvetli sağanak", 95: "Gök gürültülü",
    }
    return labels.get(_number_or_none(code), "Güncel hava")


def render_world_map() -> None:
    """TV modu için hızlı yüklenen, etkileşimli dünya haritası."""
    components.html(
        """
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <style>#tv-world-map{height:275px;border-radius:10px;overflow:hidden} body{margin:0;background:transparent}</style>
        <div id="tv-world-map"></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
          const map = L.map('tv-world-map', {zoomControl:true, attributionControl:false, worldCopyJump:true}).setView([27, 20], 2);
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18}).addTo(map);
          L.marker([37.5858, 36.9371]).addTo(map).bindPopup('<b>Kahramanmaraş</b><br>Güneş Doğalgaz').openPopup();
        </script>
        """,
        height=280,
        scrolling=False,
    )


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
    connection.execute("CREATE TABLE IF NOT EXISTS login_sessions (token TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at TEXT NOT NULL)")
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
        "global_theme": st.session_state.get("global_theme", "Aydınlık"),
        "global_notes": st.session_state.get("global_notes", ""),
        "dashboard_notes": st.session_state.get("dashboard_notes", {"daily": "", "weekly": "", "monthly": ""}),
        "master_directory_version": st.session_state.get("master_directory_version", 0),
    }, ensure_ascii=False)
    with open_database() as connection:
        connection.execute(
            "INSERT INTO application_state (id, payload, saved_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, saved_at = excluded.saved_at",
            (payload, datetime.now().isoformat(timespec="seconds")),
        )


def normalize_masters(items: list) -> list[dict]:
    return [item.copy() if isinstance(item, dict) else {"name": str(item), "number": "", "phone": ""} for item in items]


def create_login_session(username: str) -> str:
    """Tarayıcı yenilense bile girişin korunması için 30 günlük oturum anahtarı üretir."""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=30)).isoformat(timespec="seconds")
    with open_database() as connection:
        connection.execute("DELETE FROM login_sessions WHERE expires_at < ?", (datetime.now().isoformat(timespec="seconds"),))
        connection.execute("INSERT INTO login_sessions (token, username, expires_at) VALUES (?, ?, ?)", (token, username, expires_at))
    return token


def restore_login_session() -> dict | None:
    token = st.query_params.get("oturum")
    if not token:
        return None
    with open_database() as connection:
        row = connection.execute("SELECT username, expires_at FROM login_sessions WHERE token = ?", (str(token),)).fetchone()
    if not row or row[1] <= datetime.now().isoformat(timespec="seconds"):
        return None
    account = st.session_state.users.get(row[0])
    if not account:
        return None
    st.session_state.login_token = str(token)
    return {"username": row[0], **account}


def clear_login_session() -> None:
    token = st.session_state.get("login_token") or st.query_params.get("oturum")
    if token:
        with open_database() as connection:
            connection.execute("DELETE FROM login_sessions WHERE token = ?", (str(token),))
    st.query_params.clear()
    st.session_state.pop("login_token", None)


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


def has_permission(permission: str) -> bool:
    active_user = st.session_state.get("current_user", {})
    if active_user.get("role") == "admin":
        return True
    custom_permissions = active_user.get("permissions")
    allowed = set(custom_permissions) if custom_permissions is not None else ROLE_PERMISSIONS.get(active_user.get("role"), set())
    return permission in allowed


def save_office_notes() -> None:
    st.session_state.global_notes = st.session_state.office_notes
    save_state()


def save_dashboard_note(note_type: str) -> None:
    st.session_state.dashboard_notes[note_type] = st.session_state[f"note_{note_type}"]
    save_state()


def render_animated_turkey_clock() -> None:
    """TV ekranı için tarayıcıda saniye saniye güncellenen Türkiye saati."""
    components.html("""
    <style>
      body { margin:0; background:transparent; font-family:Arial,sans-serif; }
      #clock { color:#f59e0b; font-size:28px; font-weight:800; letter-spacing:1px;
        text-align:right; animation:pulse 1.5s ease-in-out infinite; }
      #label { color:#94a3b8; font-size:11px; text-align:right; margin-top:2px; }
      @keyframes pulse { 50% { opacity:.6; transform:scale(.985); } }
    </style>
    <div id="clock">--:--:--</div><div id="label">TÜRKİYE SAATİ</div>
    <script>
      const updateClock = () => {
        document.getElementById('clock').textContent = new Intl.DateTimeFormat('tr-TR',
          {timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date());
      };
      updateClock(); setInterval(updateClock, 1000);
    </script>
    """, height=55)


def reset_captcha(form_name: str) -> None:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    st.session_state[f"{form_name}_captcha_code"] = "".join(secrets.choice(alphabet) for _ in range(5))
    st.session_state.pop(f"{form_name}_captcha_answer", None)


def captcha_image(code: str) -> Image.Image:
    image = Image.new("RGB", (210, 64), "#eef2f7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for index in range(7):
        x1, y1 = secrets.randbelow(210), secrets.randbelow(64)
        x2, y2 = secrets.randbelow(210), secrets.randbelow(64)
        draw.line((x1, y1, x2, y2), fill=(170, 180, 195), width=1)
    for index, character in enumerate(code):
        draw.text((22 + index * 34, 22 + secrets.randbelow(10) - 5), character, fill="#15233d", font=font, stroke_width=1)
    return image


def render_captcha(form_name: str) -> str:
    code_key = f"{form_name}_captcha_code"
    if code_key not in st.session_state:
        reset_captcha(form_name)
    st.caption("🛡️ Güvenlik doğrulaması: Görseldeki 5 karakteri yazın.")
    st.image(captcha_image(st.session_state[code_key]), width=210)
    return st.text_input("Doğrulama kodu", key=f"{form_name}_captcha_answer", autocomplete="off")


def valid_captcha(form_name: str, answer: str) -> bool:
    expected = st.session_state.get(f"{form_name}_captcha_code", "")
    return bool(answer) and secrets.compare_digest(answer.strip().upper(), expected)


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
            login_error = st.session_state.pop("login_captcha_error", None)
            if login_error:
                st.error(login_error)
            with st.form("login_form"):
                username = st.text_input("Kullanıcı adı", autocomplete="username")
                password = st.text_input("Şifre", type="password", autocomplete="current-password")
                captcha_answer = render_captcha("login")
                submitted = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            if submitted:
                user = st.session_state.users.get(username.strip().lower())
                if not valid_captcha("login", captcha_answer):
                    reset_captcha("login")
                    st.session_state.login_captcha_error = "Doğrulama kodu hatalı. Lütfen yeni görseldeki kodu yazın."
                    st.rerun()
                elif user and user["password"] == password:
                    logged_username = username.strip().lower()
                    st.session_state.current_user = {"username": logged_username, **user}
                    st.session_state.login_token = create_login_session(logged_username)
                    st.query_params["oturum"] = st.session_state.login_token
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
        with register_tab:
            st.caption("Yeni hesaplar Personel rolüyle açılır. Admin, rolü Ayarlar alanından güncelleyebilir.")
            register_error = st.session_state.pop("register_captcha_error", None)
            if register_error:
                st.error(register_error)
            with st.form("register_form", clear_on_submit=True):
                full_name = st.text_input("Ad soyad *")
                new_username = st.text_input("Kullanıcı adı *")
                new_password = st.text_input("Şifre *", type="password")
                password_again = st.text_input("Şifre tekrar *", type="password")
                register_captcha = render_captcha("register")
                create_account = st.form_submit_button("Hesap Oluştur", type="primary", use_container_width=True)
            if create_account:
                key = new_username.strip().lower()
                if not valid_captcha("register", register_captcha):
                    reset_captcha("register")
                    st.session_state.register_captcha_error = "Doğrulama kodu hatalı. Lütfen yeni görseldeki kodu yazın."
                    st.rerun()
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
    st.markdown("""
    <style>
    [data-testid='stSidebar'],[data-testid='stHeader']{display:none}
    .block-container{max-width:100%;padding:.8rem 1.8rem}
    [data-testid='stMetric']{padding:.55rem .8rem}
    [data-testid='stMetricValue']{font-size:1.75rem}
    .tv-note{min-height:64px;max-height:64px;overflow:hidden;border:1px solid #24324a;border-radius:8px;padding:.45rem .6rem;color:#cbd5e1;font-size:.78rem;white-space:pre-wrap}
    .tv-note-title{font-size:.76rem;font-weight:800;color:#f59e0b;margin-bottom:.18rem}
    .market-panel{display:flex;flex-direction:column;gap:.22rem;min-width:208px;max-width:240px}
    .market-quote{display:grid;grid-template-columns:75px 1fr auto;align-items:center;gap:.3rem;border:1px solid #24324a;border-radius:7px;padding:.23rem .4rem;background:rgba(15,23,42,.45)}
    .market-name{font-size:.66rem;font-weight:800;color:#cbd5e1;white-space:nowrap}
    .market-value{font-size:.78rem;font-weight:800;color:#f8fafc;white-space:nowrap}
    .market-change{font-size:.58rem;font-weight:700;white-space:nowrap;text-align:right}
    .fuel-title{font-size:.63rem;font-weight:800;color:#94a3b8;margin:.2rem 0 .1rem}
    .fuel-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.18rem}
    .fuel-item{border-left:2px solid #f59e0b;padding:.16rem .22rem;background:rgba(15,23,42,.3);font-size:.57rem;color:#cbd5e1;white-space:nowrap}
    .fuel-price{display:block;color:#f8fafc;font-size:.69rem;font-weight:800;margin-top:.04rem}
    .gas-unit{margin-top:.2rem;border-left:2px solid #38bdf8;padding:.2rem .32rem;background:rgba(15,23,42,.3);font-size:.62rem;color:#cbd5e1;white-space:nowrap}
    .gas-unit strong{color:#f8fafc;font-size:.72rem}
    .weather-card{margin-top:.15rem;border:1px solid #24324a;border-radius:7px;padding:.28rem .42rem;background:rgba(15,23,42,.45);font-size:.65rem;color:#cbd5e1;white-space:nowrap}
    .weather-temp{font-size:1rem;font-weight:800;color:#f8fafc;margin-right:.3rem}
    </style>
    """, unsafe_allow_html=True)
    if st_autorefresh:
        st_autorefresh(interval=60_000, limit=None, key="tv_auto_refresh")
    logo, market, title, clock, action = st.columns([.85, 2.2, 4.25, 1.35, .9])
    with logo:
        render_logo(95)
    with market:
        rates = fetch_market_quotes()
        quote_items = [
            ("USD", "💵 USD/TL", rates.get("USD"), 4),
            ("EUR", "💶 EUR/TL", rates.get("EUR"), 4),
            ("GRAM_ALTIN", "🥇 Gram", rates.get("GRAM_ALTIN"), 2),
        ]
        quotes_html = []
        for quote_key, label, value, digits in quote_items:
            change_text, change_colour = market_change(quote_key, value)
            value_text = f"₺{value:,.{digits}f}" if value is not None else "—"
            quotes_html.append(
                f"<div class='market-quote'><div class='market-name'>{label}</div>"
                f"<div class='market-value'>{value_text}</div>"
                f"<div class='market-change' style='color:{change_colour}'>{change_text}</div></div>"
            )
        st.markdown(f"<div class='market-panel'>{''.join(quotes_html)}</div>", unsafe_allow_html=True)
        fuel_prices = fetch_kahramanmaras_fuel_prices()
        fuel_html = []
        for icon, label in [("⛽", "Benzin"), ("🚛", "Motorin"), ("🔥", "LPG")]:
            value = fuel_prices.get(label)
            value_text = f"₺{value:,.2f}" if value is not None else "—"
            fuel_html.append(f"<div class='fuel-item'>{icon} {label}<span class='fuel-price'>{value_text}/L</span></div>")
        st.markdown(
            f"<div class='fuel-title'>KAHRAMANMARAŞ AKARYAKIT</div><div class='fuel-grid'>{''.join(fuel_html)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='gas-unit'>🔥 <strong>Doğalgaz tüketimi</strong> · takip birimi: m³</div>", unsafe_allow_html=True)
        st.caption("Canlı piyasa · 60 sn")
    with title:
        st.title("☀️ Güneş Doğalgaz | Canlı Ofis Ekranı")
        st.caption(f"Son güncelleme: {turkey_now().strftime('%d.%m.%Y %H:%M')} (Türkiye)")
    with clock:
        render_animated_turkey_clock()
        weather = fetch_kahramanmaras_weather()
        temperature = weather.get("temperature")
        min_temp, max_temp = weather.get("minimum"), weather.get("maximum")
        if all(value is not None for value in (temperature, min_temp, max_temp)):
            weather_html = (
                f"<div class='weather-card'>🌤️ <b>Kahramanmaraş</b><br>"
                f"<span class='weather-temp'>{float(temperature):.0f}°</span>{weather_label(weather.get('weather_code'))}"
                f" · {float(min_temp):.0f}° / {float(max_temp):.0f}°</div>"
            )
        else:
            weather_html = "<div class='weather-card'>🌤️ Kahramanmaraş · Hava verisi bekleniyor</div>"
        st.markdown(weather_html, unsafe_allow_html=True)
    with action:
        if st.button("TV Modundan Çık", use_container_width=True):
            st.session_state.tv_mode = False
            st.rerun()
    df = get_df()
    waiting_approval = len(df[df["Surec_Adimi"] == "Armadaş Dijital Onay Bekliyor"]) if not df.empty else 0
    approved = len(df[(df["Durum"] == "Onaylandı") | (df["Surec_Adimi"] == "Armadaş Onayladı / Tesisat Aşamasında")]) if not df.empty else 0
    active = len(df[df["Durum"] == "Devam Ediyor"]) if not df.empty else 0
    rejected = len(df[(df["Durum"] == "Reddedildi") | (df["Surec_Adimi"] == "Armadaş Eksik / Red Aldı") | df["Diger_Islemler"].fillna("").str.contains("Randevu Reddi", na=False)]) if not df.empty else 0
    a, b, c, d = st.columns(4)
    a.metric("⏳ Onay Bekleyen", f"{waiting_approval} proje")
    b.metric("✅ Onaylanan", f"{approved} proje")
    c.metric("🛠️ Devam Eden İş", f"{active} proje")
    d.metric("❌ Reddedilen", f"{rejected} proje")
    st.markdown("---")
    note_daily, note_weekly, note_monthly = st.columns(3)
    notes = st.session_state.get("dashboard_notes", {})
    for column, title, note_key in [
        (note_daily, "📅 GÜNLÜK NOT", "daily"),
        (note_weekly, "🗓️ HAFTALIK NOT", "weekly"),
        (note_monthly, "📆 AYLIK NOT", "monthly"),
    ]:
        with column:
            note_text = html.escape(str(notes.get(note_key, "") or "Not bulunmuyor.")[:220]).replace("\n", "<br>")
            st.markdown(f"<div class='tv-note-title'>{title}</div><div class='tv-note'>{note_text}</div>", unsafe_allow_html=True)
    st.markdown("---")
    charts_column, map_column = st.columns([3, 1])
    with charts_column:
        if df.empty:
            st.info("Grafik göstermek için proje kaydı ekleyin.")
        else:
            chart_df = df.dropna(subset=["Tarih"]).copy()
            chart_df["Hafta"] = chart_df["Tarih"].dt.to_period("W-MON").apply(lambda period: period.start_time.strftime("%d.%m"))
            weekly = chart_df.groupby("Hafta", as_index=False).agg(Ciro=("Tutar", "sum")).tail(8)
            monthly = chart_df.groupby("Ay", as_index=False).agg(Ciro=("Tutar", "sum")).tail(6)
            master_projects = chart_df.groupby("Usta", as_index=False).agg(**{"Proje Adedi": ("Proje", "count")}).sort_values("Proje Adedi", ascending=False)
            left_chart, right_chart = st.columns(2)
            with left_chart:
                st.markdown("##### 📅 Haftalık Ciro")
                st.bar_chart(weekly.set_index("Hafta"), height=120, color="#167d9a")
            with right_chart:
                st.markdown("##### 🗓️ Aylık Ciro")
                st.bar_chart(monthly.set_index("Ay"), height=120, color="#2a9d8f")
            st.markdown("##### 👷 Ustaların Proje Adetleri")
            st.bar_chart(master_projects.set_index("Usta"), height=145, color="#f4a261")
    with map_column:
        st.markdown("##### 🌍 Dünya Haritası")
        render_world_map()
    st.caption("Tam ekran kullanım için tarayıcıda F11 tuşuna basın.")


if "storage_loaded" not in st.session_state:
    saved = read_saved_state()
    if saved:
        st.session_state.projects = saved.get("projects", [])
        st.session_state.masters = normalize_masters(saved.get("masters", DEFAULT_MASTERS))
        st.session_state.users = saved.get("users", {key: value.copy() for key, value in DEFAULT_USERS.items()})
        st.session_state.global_theme = saved.get("global_theme", "Aydınlık")
        st.session_state.global_notes = saved.get("global_notes", "")
        st.session_state.dashboard_notes = saved.get("dashboard_notes", {"daily": saved.get("global_notes", ""), "weekly": "", "monthly": ""})
        st.session_state.master_directory_version = saved.get("master_directory_version", 0)
    else:
        # İlk kayıt anında varsa eski oturum verisini korur, sonra sunucuya kaydeder.
        current_projects = list(st.session_state.get("projects", []))
        st.session_state.projects = current_projects or list(st.session_state.get("projeler", []))
        st.session_state.masters = normalize_masters(st.session_state.get("masters", DEFAULT_MASTERS))
        for legacy_master in normalize_masters(st.session_state.get("ustalar", [])):
            if legacy_master["name"] and not any(master["name"] == legacy_master["name"] for master in st.session_state.masters):
                st.session_state.masters.append(legacy_master)
        st.session_state.users = st.session_state.get("users", {key: value.copy() for key, value in DEFAULT_USERS.items()})
        st.session_state.global_theme = st.session_state.get("global_theme", "Aydınlık")
        st.session_state.global_notes = st.session_state.get("global_notes", "")
        st.session_state.dashboard_notes = st.session_state.get("dashboard_notes", {"daily": st.session_state.global_notes, "weekly": "", "monthly": ""})
        st.session_state.master_directory_version = 0
        save_state()
    st.session_state.storage_loaded = True

if st.session_state.get("master_directory_version", 0) < 2:
    # Yeni usta rehberini mevcut kullanıcı eklemelerini silmeden bir kez birleştirir.
    for directory_master in DEFAULT_MASTERS:
        present = next((master for master in st.session_state.masters if master["name"] == directory_master["name"]), None)
        if present is None:
            st.session_state.masters.append(directory_master.copy())
        elif not present.get("phone") and directory_master["phone"]:
            present["phone"] = directory_master["phone"]
    st.session_state.master_directory_version = 2
    save_state()
if "theme" not in st.session_state:
    st.session_state.theme = st.session_state.get("global_theme", "Aydınlık")
if "tv_mode" not in st.session_state:
    st.session_state.tv_mode = False

if "current_user" not in st.session_state:
    resumed_user = restore_login_session()
    if resumed_user:
        st.session_state.current_user = resumed_user
if "current_user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state.current_user
role = user["role"]
st.session_state.theme = st.session_state.global_theme
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
        st.session_state.global_theme = new_theme
        save_state()
        st.rerun()
    st.success(f"👤 {user['name']}\n\n{ROLES[role]}")
    if st.button("💾 Verileri Sunucuya Kaydet", use_container_width=True):
        save_state()
        st.success("Veriler site kayıt alanına kaydedildi.")
    if st.button("📺 TV Modunu Aç", use_container_width=True):
        st.session_state.tv_mode = True
        st.rerun()
    if st.button("↪ Çıkış Yap", use_container_width=True):
        clear_login_session()
        del st.session_state.current_user
        st.rerun()
    st.caption("☁️ Otomatik kayıt açık")

if st_autorefresh:
    st_autorefresh(interval=60_000, limit=None, key="office_auto_refresh")

head_logo, head_title, head_clock = st.columns([1, 7, 1])
with head_logo:
    render_logo(82)
with head_title:
    st.markdown("<p class='brand-title'>☀️ Güneş Doğalgaz | Dashboard</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='brand-subtitle'>{date.today().strftime('%d.%m.%Y')} · {user['name']} ({ROLES[role]})</p>", unsafe_allow_html=True)
with head_clock:
    st.markdown(f"<div class='clock'>🕒 {turkey_now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

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
    st.subheader("🗒️ Ofis Notları")
    st.caption("Notlar otomatik kaydedilir. Silmek isterseniz metni klavyeden temizlemeniz yeterlidir.")
    for note_type in ["daily", "weekly", "monthly"]:
        state_key = f"note_{note_type}"
        if state_key not in st.session_state:
            st.session_state[state_key] = st.session_state.dashboard_notes.get(note_type, "")
    daily_note, weekly_note, monthly_note = st.columns(3)
    with daily_note:
        st.text_area("📅 Günlük Notlar", key="note_daily", height=155, on_change=lambda: save_dashboard_note("daily"))
    with weekly_note:
        st.text_area("🗓️ Haftalık Notlar", key="note_weekly", height=155, on_change=lambda: save_dashboard_note("weekly"))
    with monthly_note:
        st.text_area("📆 Aylık Notlar", key="note_monthly", height=155, on_change=lambda: save_dashboard_note("monthly"))
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
            job_status = st.selectbox("İş durumu", ["Devam Ediyor", "Onaylandı", "Reddedildi", "Tamamlandı", "Beklemede"])
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
    if not has_permission("project_edit"):
        st.warning("✏️ Bu kullanıcı için kayıt düzenleme izni yok.")
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
                status_options = ["Devam Ediyor", "Onaylandı", "Reddedildi", "Tamamlandı", "Beklemede"]
                edit_status = st.selectbox("Durum", status_options, index=status_options.index(record["Durum"]) if record["Durum"] in status_options else 0)
                edit_amount = st.number_input("Proje bedeli", min_value=0.0, value=float(record["Tutar"]), step=1000.0)
                edit_payment = st.number_input("Tahsilat", min_value=0.0, max_value=float(edit_amount), value=min(float(record["Tahsilat"]), float(edit_amount)), step=1000.0)
                edit_debt = st.number_input("Ofis borcu / gideri", min_value=0.0, value=float(record.get("Ofis_Borcu", 0)), step=500.0)
            save = st.form_submit_button("Değişiklikleri Kaydet", type="primary")
        if save:
            record.update({"Tarih": str(edit_date), "Ay": edit_date.strftime("%Y-%m"), "Müşteri": edit_customer.strip(), "Proje": edit_project.strip(), "Usta": edit_master, "Durum": edit_status, "Tutar": edit_amount, "Tahsilat": edit_payment, "Ofis_Borcu": edit_debt})
            save_state()
            st.success("Kayıt güncellendi.")
            st.rerun()
        if has_permission("project_delete") and st.button("🗑️ Seçili kaydı sil", type="secondary"):
            st.session_state.projects.pop(index)
            save_state()
            st.warning("Kayıt silindi.")
            st.rerun()

with tab5:
    st.subheader("⚙️ Ayarlar ve Yönetim")
    if not has_permission("masters_manage") and not has_permission("users_manage"):
        st.warning("Bu kullanıcı için yönetim izni yok.")
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
        if has_permission("users_manage"):
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
                x1, x2, x3, x4 = st.columns(4)
                changed_user_name = x1.text_input("Ad soyad", value=edited["name"])
                changed_user_role = x2.selectbox("Rol", list(ROLES), index=list(ROLES).index(edited["role"]), format_func=lambda value: ROLES[value])
                changed_password = x3.text_input("Yeni şifre (boş bırakılabilir)", type="password")
                current_permissions = edited.get("permissions", list(ROLE_PERMISSIONS.get(edited["role"], set())))
                changed_permissions = x4.multiselect("Ek izinler", list(PERMISSION_LABELS), default=current_permissions, format_func=lambda value: PERMISSION_LABELS[value])
                save_user = st.form_submit_button("💾 Kullanıcıyı Güncelle", type="primary")
            if save_user:
                if not changed_user_name.strip() or (changed_password and len(changed_password) < 6):
                    st.error("Ad soyad zorunlu; yeni şifre en az 6 karakter olmalı.")
                else:
                    edited.update({"name": changed_user_name.strip(), "role": changed_user_role, "permissions": changed_permissions})
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
