"""Local events — fetch and parse iCal/RSS/HTML feeds from community calendars."""

from __future__ import annotations

import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

from icalendar import Calendar

from assistant import config
from assistant.storage.database import get_connection, init_db


def parse_ical_feed(data: bytes, source: str) -> list[dict]:
    """Parse raw iCal bytes into a list of event dicts."""
    cal = Calendar.from_ical(data)
    events = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        uid = str(component.get("UID", ""))
        summary = str(component.get("SUMMARY", ""))
        description = str(component.get("DESCRIPTION", ""))
        location = str(component.get("LOCATION", ""))
        raw_url = str(component.get("URL", ""))
        # Fix relative URLs (e.g., Harrisburg feeds return paths like /common/...)
        if raw_url and not raw_url.startswith("http"):
            raw_url = ""
        url = raw_url
        organizer = str(component.get("ORGANIZER", ""))

        # Categories can be a list or single value
        cat_prop = component.get("CATEGORIES")
        if cat_prop:
            if isinstance(cat_prop, list):
                categories = ",".join(str(c) for group in cat_prop for c in group.cats)
            else:
                categories = ",".join(str(c) for c in cat_prop.cats)
        else:
            categories = ""

        # Parse start date/time
        dtstart = component.get("DTSTART")
        if not dtstart:
            continue
        dt = dtstart.dt
        if isinstance(dt, datetime):
            start_date = dt.strftime("%Y-%m-%d")
            start_time = dt.strftime("%H:%M")
        elif isinstance(dt, date):
            start_date = dt.isoformat()
            start_time = None
        else:
            continue

        # Parse end date/time
        dtend = component.get("DTEND")
        end_date = None
        end_time = None
        if dtend:
            dte = dtend.dt
            if isinstance(dte, datetime):
                end_date = dte.strftime("%Y-%m-%d")
                end_time = dte.strftime("%H:%M")
            elif isinstance(dte, date):
                end_date = dte.isoformat()

        events.append({
            "uid": uid,
            "source": source,
            "title": summary,
            "description": description,
            "location": location,
            "start_date": start_date,
            "start_time": start_time,
            "end_date": end_date,
            "end_time": end_time,
            "categories": categories,
            "organizer": organizer,
            "url": url,
        })

    return events


def parse_rss_feed(data: bytes, source: str) -> list[dict]:
    """Parse RSS XML bytes into a list of event dicts."""
    root = ET.fromstring(data)
    events = []

    # Detect namespaces (e.g., BiblioCommons uses bc:start_date)
    ns = {}
    for prefix, uri in [
        ("bc", "http://bibliocommons.com/rss/1.0/modules/event/"),
        ("dc", "http://purl.org/dc/elements/1.1/"),
    ]:
        ns[prefix] = uri

    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link or "").strip()

        # Try multiple date sources
        start_date = None
        start_time = None
        end_date = None
        end_time = None

        # 1. BiblioCommons bc:start_date / bc:end_date
        bc_start = item.findtext(f"{{{ns['bc']}}}start_date")
        bc_end = item.findtext(f"{{{ns['bc']}}}end_date")
        if bc_start:
            try:
                dt = datetime.fromisoformat(bc_start)
                start_date = dt.strftime("%Y-%m-%d")
                start_time = dt.strftime("%H:%M") if dt.hour or dt.minute else None
            except (ValueError, TypeError):
                start_date = bc_start[:10] if len(bc_start) >= 10 else None
        if bc_end:
            try:
                dt = datetime.fromisoformat(bc_end)
                end_date = dt.strftime("%Y-%m-%d")
                end_time = dt.strftime("%H:%M") if dt.hour or dt.minute else None
            except (ValueError, TypeError):
                pass

        # 2. Standard pubDate
        if not start_date:
            pub_date_str = item.findtext("pubDate") or ""
            if pub_date_str:
                try:
                    dt = parsedate_to_datetime(pub_date_str)
                    start_date = dt.strftime("%Y-%m-%d")
                    start_time = dt.strftime("%H:%M") if dt.hour or dt.minute else None
                except (ValueError, TypeError):
                    pass

        if not start_date:
            continue  # Skip events with no parseable date

        # Generate stable UID from guid
        uid = hashlib.sha256(f"{source}:{guid}".encode()).hexdigest()[:32]

        # Location from bc:location nested element
        location = ""
        bc_loc = item.find(f"{{{ns['bc']}}}location")
        if bc_loc is not None:
            loc_name = (bc_loc.findtext(f"{{{ns['bc']}}}name") or "").strip()
            loc_city = (bc_loc.findtext(f"{{{ns['bc']}}}city") or "").strip()
            if loc_name and loc_city:
                location = f"{loc_name}, {loc_city}"
            elif loc_name:
                location = loc_name

        # Check if virtual
        is_virtual = (item.findtext(f"{{{ns['bc']}}}is_virtual") or "").strip()
        if not location and is_virtual == "true":
            location = "Virtual"

        categories = ""
        for cat in item.iter("category"):
            if cat.text:
                categories = cat.text if not categories else f"{categories},{cat.text}"

        events.append({
            "uid": uid,
            "source": source,
            "title": title,
            "description": description,
            "location": location,
            "start_date": start_date,
            "start_time": start_time,
            "end_date": end_date,
            "end_time": end_time,
            "categories": categories,
            "organizer": "",
            "url": link,
        })

    return events


def scrape_untappd_events(url: str, source: str, venue_name: str = "") -> list[dict]:
    """Scrape events from an Untappd venue events page."""
    req = urllib.request.Request(url, headers={"User-Agent": "PersonalAssistant/0.1"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    events = []
    # Parse event blocks: <p class="date">...</p> followed by <h4 class="name"><a href="...">
    date_times = re.findall(r'class="date"[^>]*>(.*?)</p>', html, re.DOTALL)
    titles = re.findall(r'class="name"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)

    for i, dt_raw in enumerate(date_times):
        if i >= len(titles):
            break

        event_url, title = titles[i]
        title = re.sub(r"<[^>]+>", "", title).strip()
        if not event_url.startswith("http"):
            event_url = f"https://untappd.com{event_url}"

        # Parse date: "Sun, Mar 29th • 5:00 PM EDT - Sun, Mar 29th • 7:00 PM EDT"
        dt_clean = re.sub(r"<[^>]+>", "", dt_raw).strip()
        # Extract start portion (before the dash)
        parts = dt_clean.split(" - ")
        start_part = parts[0].strip()

        # Parse: "Sun, Mar 29th • 5:00 PM EDT"
        match = re.match(
            r'\w+,\s+(\w+)\s+(\d+)\w*\s*•\s*(\d+:\d+\s*[AP]M)',
            start_part
        )
        if not match:
            continue

        month_str, day_str, time_str = match.groups()
        # Determine year (assume current or next year)
        today = date.today()
        try:
            parsed = datetime.strptime(f"{month_str} {day_str} {today.year} {time_str}", "%b %d %Y %I:%M %p")
            if parsed.date() < today:
                parsed = parsed.replace(year=today.year + 1)
        except ValueError:
            continue

        start_date = parsed.strftime("%Y-%m-%d")
        start_time = parsed.strftime("%H:%M")

        # Parse end time if available
        end_date = None
        end_time = None
        if len(parts) > 1:
            end_match = re.search(r'(\d+:\d+\s*[AP]M)', parts[1])
            if end_match:
                try:
                    end_parsed = datetime.strptime(f"{month_str} {day_str} {today.year} {end_match.group(1)}", "%b %d %Y %I:%M %p")
                    if end_parsed.date() < today:
                        end_parsed = end_parsed.replace(year=today.year + 1)
                    end_date = end_parsed.strftime("%Y-%m-%d")
                    end_time = end_parsed.strftime("%H:%M")
                except ValueError:
                    pass

        uid = hashlib.sha256(f"{source}:{event_url}".encode()).hexdigest()[:32]

        events.append({
            "uid": uid,
            "source": source,
            "title": title,
            "description": "",
            "location": venue_name,
            "start_date": start_date,
            "start_time": start_time,
            "end_date": end_date,
            "end_time": end_time,
            "categories": "Brewery",
            "organizer": "",
            "url": event_url,
        })

    return events


def _get_conn(conn=None):
    """Get a database connection, creating one if not provided."""
    if conn is not None:
        return conn
    c = get_connection(config.DB_PATH)
    init_db(c)
    return c


def cache_events(events: list[dict], conn=None) -> int:
    """Upsert events into the local_events table. Returns count of events stored."""
    db = _get_conn(conn)
    count = 0
    for e in events:
        db.execute("""
            INSERT INTO local_events (uid, source, title, description, location,
                start_date, start_time, end_date, end_time, categories, organizer, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                location=excluded.location,
                start_date=excluded.start_date,
                start_time=excluded.start_time,
                end_date=excluded.end_date,
                end_time=excluded.end_time,
                categories=excluded.categories,
                organizer=excluded.organizer,
                url=excluded.url,
                fetched_at=CURRENT_TIMESTAMP
        """, (
            e["uid"], e["source"], e["title"], e["description"], e["location"],
            e["start_date"], e["start_time"], e["end_date"], e["end_time"],
            e["categories"], e["organizer"], e["url"],
        ))
        count += 1
    db.commit()
    return count


def get_events_between(start: str, end: str, conn=None, filtered: bool = True) -> list[dict]:
    """Get cached events where start_date falls within [start, end] inclusive."""
    db = _get_conn(conn)
    rows = db.execute(
        """SELECT * FROM local_events
           WHERE start_date >= ? AND start_date <= ?
           ORDER BY start_date, start_time""",
        (start, end),
    ).fetchall()
    events = [dict(r) for r in rows]
    if filtered:
        events = _filter_events(events)
    return events


def _filter_events(events: list[dict]) -> list[dict]:
    """Filter out noise: distant parks, recurring tours, government meetings."""
    exclude_keywords = config.LOCAL_EVENTS_EXCLUDE_KEYWORDS
    nearby_parks = config.NC_PARKS_NEARBY

    filtered = []
    for e in events:
        title = e.get("title", "")
        location = e.get("location", "")
        source = e.get("source", "")

        # Skip events matching exclude keywords
        if any(kw.lower() in title.lower() for kw in exclude_keywords):
            continue

        # For NC State Parks, only keep nearby parks
        if source == "nc_state_parks":
            if not any(park.lower() in location.lower() or park.lower() in title.lower()
                       for park in nearby_parks):
                continue

        # For CML Library, skip adult-only events (keep kid/family/all-ages)
        if source == "cml_library":
            cats = e.get("categories", "").lower()
            family_tags = ("babies", "toddler", "preschool", "school age",
                           "preteens", "storytime", "family", "youth")
            adult_only_tags = ("adults", "older adults", "new adults")
            has_family = any(tag in cats for tag in family_tags)
            has_only_adult = any(tag in cats for tag in adult_only_tags) and not has_family
            if has_only_adult:
                continue

        filtered.append(e)

    # Sort: nearby events first, then by date/time
    filtered.sort(key=lambda e: (_location_priority(e), e.get("start_date", ""), e.get("start_time") or ""))
    return filtered


def _location_priority(event: dict) -> int:
    """Return 0 for priority locations, 1 for local sources without location, 2 for others."""
    location = (event.get("location") or "").lower()
    title = (event.get("title") or "").lower()
    description = (event.get("description") or "").lower()
    source = event.get("source", "")

    # Check priority locations
    for loc in config.LOCAL_EVENTS_PRIORITY_LOCATIONS:
        if loc in location or loc in title or loc in description:
            return 0

    # Cabarrus County / Harrisburg / local brewery sources are inherently local
    local_sources = ("cabarrus_community", "harrisburg_events", "harrisburg_community",
                     "harrisburg_parks", "cabarrus_brewing", "percent_taphouse",
                     "southern_strain", "luck_factory")
    if source in local_sources:
        return 0

    # Events with no location — unknown distance
    if not location:
        return 2

    return 1


def fetch_feed(url: str, source: str, feed_type: str = "ical", conn=None) -> int:
    """Fetch a feed URL, parse, and cache events. feed_type is 'ical' or 'rss'."""
    req = urllib.request.Request(url, headers={"User-Agent": "PersonalAssistant/0.1"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    if feed_type == "rss":
        events = parse_rss_feed(data, source=source)
    else:
        events = parse_ical_feed(data, source=source)
    return cache_events(events, conn=conn)


def feeds_are_stale(max_age_hours: int = 12, conn=None) -> bool:
    """Check if cached events are older than max_age_hours."""
    db = _get_conn(conn)
    row = db.execute(
        "SELECT MAX(fetched_at) as latest FROM local_events"
    ).fetchone()
    if not row or not row["latest"]:
        return True
    latest = datetime.fromisoformat(row["latest"])
    return datetime.now() - latest > timedelta(hours=max_age_hours)


def refresh_all_feeds(conn=None) -> dict[str, int]:
    """Fetch all configured feeds and cache events. Returns {source: count}."""
    results = {}
    for source, url in config.LOCAL_EVENT_FEEDS_ICAL.items():
        try:
            count = fetch_feed(url, source, feed_type="ical", conn=conn)
            results[source] = count
        except Exception:
            results[source] = -1
    for source, url in config.LOCAL_EVENT_FEEDS_RSS.items():
        try:
            count = fetch_feed(url, source, feed_type="rss", conn=conn)
            results[source] = count
        except Exception:
            results[source] = -1
    for source, info in config.LOCAL_EVENT_UNTAPPD.items():
        try:
            events = scrape_untappd_events(info["url"], source, venue_name=info["venue"])
            count = cache_events(events, conn=conn)
            results[source] = count
        except Exception:
            results[source] = -1
    return results
