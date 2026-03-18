"""Centralized configuration and paths."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.environ.get("ASSISTANT_DATA_DIR", PROJECT_ROOT / "data"))
DB_PATH = DATA_DIR / "assistant.db"

# Load .env from data dir if present
_env_file = DATA_DIR / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

GOOGLE_CREDENTIALS_PATH = Path(
    os.environ.get("GOOGLE_CREDENTIALS_PATH", DATA_DIR / "google_credentials.json")
)
GOOGLE_TOKENS_DIR = DATA_DIR / "tokens"

# Known Google accounts — alias -> email
GOOGLE_ACCOUNTS = {
    "personal": "christopher.singer.analytics@gmail.com",
    "crossfit": "csinger1.crossfit@gmail.com",
}

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN", "")


def google_token_path(account: str = "personal") -> Path:
    """Get the token path for a named account."""
    GOOGLE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    return GOOGLE_TOKENS_DIR / f"token_{account}.json"


# Local event feeds — iCal (.ics) and RSS (.xml) formats
LOCAL_EVENT_FEEDS_ICAL = {
    "cabarrus_community": "https://go.activecalendar.com/cabarruscounty/site/community/page/ical",
    "harrisburg_events": "https://www.harrisburgnc.gov/common/modules/iCalendar/iCalendar.aspx?catID=14&feed=calendar",
    "harrisburg_community": "https://www.harrisburgnc.gov/common/modules/iCalendar/iCalendar.aspx?catID=28&feed=calendar",
    "harrisburg_parks": "https://www.harrisburgnc.gov/common/modules/iCalendar/iCalendar.aspx?catID=24&feed=calendar",
    "nc_state_parks": "https://events.dncr.nc.gov/department/north-carolina-state-parks-and-recreation/calendar.ics",
}

LOCAL_EVENT_FEEDS_RSS = {
    "cml_library": "https://gateway.bibliocommons.com/v2/libraries/cmlibrary/rss/events",
}

# Combined for backward compat
LOCAL_EVENT_FEEDS = LOCAL_EVENT_FEEDS_ICAL
