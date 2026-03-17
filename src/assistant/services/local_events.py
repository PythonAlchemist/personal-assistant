"""Local events — fetch and parse iCal feeds from community calendars."""

from __future__ import annotations

import urllib.request
from datetime import date, datetime

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
        url = str(component.get("URL", ""))
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


def get_events_between(start: str, end: str, conn=None) -> list[dict]:
    """Get cached events where start_date falls within [start, end] inclusive."""
    db = _get_conn(conn)
    rows = db.execute(
        """SELECT * FROM local_events
           WHERE start_date >= ? AND start_date <= ?
           ORDER BY start_date, start_time""",
        (start, end),
    ).fetchall()
    return [dict(r) for r in rows]
