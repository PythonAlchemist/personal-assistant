"""Tests for local events service."""

import sqlite3
from assistant.storage.database import get_connection, init_db


def test_local_events_table_exists():
    conn = get_connection(":memory:")
    init_db(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='local_events'"
    )
    assert cursor.fetchone() is not None
    conn.close()


from assistant.services.local_events import parse_ical_feed, cache_events, get_events_between


SAMPLE_ICAL = b"""\
BEGIN:VCALENDAR
PRODID:-//Test//Test//EN
VERSION:2.0
BEGIN:VEVENT
UID:test-event-001@example.com
DTSTART:20260321T100000
DTEND:20260321T120000
SUMMARY:Spring Family Festival
DESCRIPTION:Fun for the whole family!
LOCATION:Town Park, Harrisburg NC
CATEGORIES:Family,Festival
ORGANIZER:mailto:events@example.com
URL:https://example.com/event/1
END:VEVENT
BEGIN:VEVENT
UID:test-event-002@example.com
DTSTART;VALUE=DATE:20260322
SUMMARY:Farmers Market
DESCRIPTION:Fresh produce and crafts.
LOCATION:Main Street
CATEGORIES:Market
END:VEVENT
END:VCALENDAR
"""


def test_cache_events_and_query(db):
    events = parse_ical_feed(SAMPLE_ICAL, source="test")
    cache_events(events, conn=db)

    # Query for the date range covering both events
    results = get_events_between("2026-03-21", "2026-03-22", conn=db)
    assert len(results) == 2
    assert results[0]["title"] == "Spring Family Festival"
    assert results[1]["title"] == "Farmers Market"


def test_cache_events_deduplicates(db):
    events = parse_ical_feed(SAMPLE_ICAL, source="test")
    cache_events(events, conn=db)
    cache_events(events, conn=db)  # Insert again

    results = get_events_between("2026-03-21", "2026-03-22", conn=db)
    assert len(results) == 2  # No duplicates


def test_parse_ical_feed():
    events = parse_ical_feed(SAMPLE_ICAL, source="test")
    assert len(events) == 2

    e1 = events[0]
    assert e1["uid"] == "test-event-001@example.com"
    assert e1["title"] == "Spring Family Festival"
    assert e1["start_date"] == "2026-03-21"
    assert e1["start_time"] == "10:00"
    assert e1["end_date"] == "2026-03-21"
    assert e1["end_time"] == "12:00"
    assert e1["location"] == "Town Park, Harrisburg NC"
    assert "Family" in e1["categories"]
    assert e1["source"] == "test"

    e2 = events[1]
    assert e2["uid"] == "test-event-002@example.com"
    assert e2["start_date"] == "2026-03-22"
    assert e2["start_time"] is None  # all-day event
    assert e2["title"] == "Farmers Market"
