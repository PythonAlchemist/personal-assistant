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
    "cabarrus_brewing": "https://www.cabarrusbrewing.com/events/?ical=1",
}

LOCAL_EVENT_FEEDS_RSS = {
    "cml_library": "https://gateway.bibliocommons.com/v2/libraries/cmlibrary/rss/events",
}

# NC State Parks near Harrisburg (within ~60 miles)
NC_PARKS_NEARBY = {
    "Lake Norman", "Morrow Mountain", "Reed Gold Mine",
    "Uwharrie", "Crowders Mountain", "South Mountains",
    "Duke Power", "Latta Plantation", "McDowell",
}

# Keywords that indicate non-family or recurring noise events to filter out
LOCAL_EVENTS_EXCLUDE_KEYWORDS = [
    "Daily Tours",
    "Board Meeting",
    "Advisory Board",
    "Crime Prevention",
    "Commissioners",
    "Soil and Water",
    "PARTF Meeting",
    "Cabarrus Summit",
    "Work Session",
]

# Priority locations — events here sort to the top
LOCAL_EVENTS_PRIORITY_LOCATIONS = [
    "harrisburg", "concord", "university city", "kannapolis",
]

# Source landing pages — fallback link when individual event URLs aren't available
LOCAL_EVENT_SOURCE_URLS = {
    "cabarrus_community": "https://go.activecalendar.com/cabarruscounty/site/community",
    "harrisburg_events": "https://www.harrisburgnc.gov/calendar.aspx?CID=14",
    "harrisburg_community": "https://www.harrisburgnc.gov/calendar.aspx?CID=28",
    "harrisburg_parks": "https://www.harrisburgnc.gov/calendar.aspx?CID=24",
    "nc_state_parks": "https://www.ncparks.gov/events",
    "cml_library": "https://cmlibrary.bibliocommons.com/events",
    "cabarrus_brewing": "https://www.cabarrusbrewing.com/events-calendar/",
    "percent_taphouse": "https://untappd.com/v/percent-tap-house/8324335/events",
    "southern_strain": "https://untappd.com/v/southern-strain-brewing-company/8995244/events",
}

# Untappd venue event pages (HTML scrape)
LOCAL_EVENT_UNTAPPD = {
    "percent_taphouse": {
        "url": "https://untappd.com/v/percent-tap-house/8324335/events",
        "venue": "Percent Taphouse, Harrisburg",
    },
    "southern_strain": {
        "url": "https://untappd.com/v/southern-strain-brewing-company/8995244/events",
        "venue": "Southern Strain Brewing, Concord",
    },
}

# Combined for backward compat
LOCAL_EVENT_FEEDS = LOCAL_EVENT_FEEDS_ICAL
