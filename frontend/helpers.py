import html
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

API_URL = "http://localhost:8000/api"
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"


def load_css() -> None:
    css_path = BASE_DIR / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_template(template_name: str, context: Optional[Dict[str, str]] = None) -> str:
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        return ""

    content = template_path.read_text(encoding="utf-8")
    if context:
        for key, value in context.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
    return content


def _safe_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None


def _safe_post(url: str) -> bool:
    try:
        response = requests.post(url, timeout=30)
        return response.status_code == 200
    except requests.RequestException:
        return False


def parse_rok(rok_prijave: Optional[str]) -> Optional[datetime]:
    if not rok_prijave:
        return None
    try:
        return datetime.fromisoformat(rok_prijave.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_iznos(value: Any) -> str:
    try:
        return f"{float(value):,.0f} EUR"
    except (TypeError, ValueError):
        return "N/A"


def safe_text(value: Any) -> str:
    if value is None:
        return "N/A"
    return html.escape(str(value))


@st.cache_data(ttl=300)
def fetch_statistics() -> Optional[Dict[str, Any]]:
    data = _safe_get(f"{API_URL}/statistics")
    if isinstance(data, dict):
        return data
    return None


@st.cache_data(ttl=300)
def fetch_natjecaji(active_only: bool = False) -> List[Dict[str, Any]]:
    data = _safe_get(f"{API_URL}/natjecaji", params={"active_only": active_only})
    if isinstance(data, list):
        return data
    return []


@st.cache_data(ttl=300)
def fetch_expiring_soon(days: int = 30) -> List[Dict[str, Any]]:
    data = _safe_get(f"{API_URL}/natjecaji/expiring/soon", params={"days": days})
    if isinstance(data, list):
        return data
    return []


def search_natjecaji(
    search_term: Optional[str] = None,
    kategorija: Optional[str] = None,
    podrucje: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, str] = {}
    if search_term:
        params["q"] = search_term
    if kategorija:
        params["kategorija"] = kategorija
    if podrucje:
        params["podrucje"] = podrucje

    data = _safe_get(f"{API_URL}/search", params=params)
    if isinstance(data, list):
        return data
    return []


def trigger_scraping() -> bool:
    return _safe_post(f"{API_URL}/scrape")


def fetch_scraping_logs(limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    data = _safe_get(f"{API_URL}/logs/scraping", params={"limit": limit})
    if isinstance(data, list):
        return data
    return None
