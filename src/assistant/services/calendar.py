"""Google Calendar integration."""

from __future__ import annotations

from datetime import datetime, timedelta, date

from assistant.services.google_auth import get_service


def _get_service(account: str = "personal"):
    return get_service("calendar", "v3", account)


def list_calendars(account: str = "personal") -> list[dict]:
    """List all calendars the user has access to."""
    service = _get_service(account)
    result = service.calendarList().list().execute()
    return [
        {
            "id": cal["id"],
            "summary": cal.get("summary", ""),
            "primary": cal.get("primary", False),
        }
        for cal in result.get("items", [])
    ]


def list_events(
    start: datetime,
    end: datetime,
    calendar_id: str = "primary",
    max_results: int = 50,
    account: str = "personal",
) -> list[dict]:
    """List events in a time range."""
    service = _get_service(account)
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start.isoformat() + "Z" if not start.tzinfo else start.isoformat(),
            timeMax=end.isoformat() + "Z" if not end.tzinfo else end.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return [_parse_event(e) for e in result.get("items", [])]


def get_todays_agenda(calendar_id: str = "primary", account: str = "personal") -> list[dict]:
    """Get all events for today."""
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return list_events(start, end, calendar_id, account=account)


def get_week_agenda(calendar_id: str = "primary", account: str = "personal") -> list[dict]:
    """Get events for the current week (today through 7 days out)."""
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return list_events(start, end, calendar_id, account=account)


def create_event(
    summary: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
    attendees: list[str] | None = None,
    recurrence: list[str] | None = None,
    account: str = "personal",
) -> dict:
    """Create a new calendar event."""
    service = _get_service(account)
    event_body = {
        "summary": summary,
        "start": _format_datetime(start),
        "end": _format_datetime(end),
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]
    if recurrence:
        event_body["recurrence"] = recurrence

    result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    return _parse_event(result)


def delete_event(event_id: str, calendar_id: str = "primary", account: str = "personal") -> None:
    """Delete an event."""
    service = _get_service(account)
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def find_free_slots(
    duration_minutes: int = 60,
    days_ahead: int = 7,
    start_hour: int = 9,
    end_hour: int = 17,
    calendar_id: str = "primary",
    account: str = "personal",
) -> list[dict]:
    """Find free time slots of a given duration in the next N days."""
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days_ahead)

    events = list_events(start, end, calendar_id, account=account)
    slots = []

    for day_offset in range(days_ahead):
        day = start + timedelta(days=day_offset)
        if day.date() < now.date():
            continue

        day_start = day.replace(hour=start_hour, minute=0)
        day_end = day.replace(hour=end_hour, minute=0)

        # If today, don't show slots that already passed
        if day.date() == now.date():
            day_start = max(day_start, now.replace(second=0, microsecond=0))

        # Get events for this day
        day_events = [
            e for e in events
            if e.get("start_dt") and day.date() == _parse_dt(e["start"]).date()
        ]
        day_events.sort(key=lambda e: e["start"])

        # Walk through the day finding gaps
        cursor = day_start
        for event in day_events:
            evt_start = _parse_dt(event["start"])
            evt_end = _parse_dt(event["end"])
            if evt_start > cursor:
                gap_minutes = (evt_start - cursor).total_seconds() / 60
                if gap_minutes >= duration_minutes:
                    slots.append({
                        "start": cursor.isoformat(),
                        "end": evt_start.isoformat(),
                        "duration_minutes": int(gap_minutes),
                        "date": day.strftime("%A %Y-%m-%d"),
                    })
            cursor = max(cursor, evt_end)

        # Check remaining time at end of day
        if cursor < day_end:
            gap_minutes = (day_end - cursor).total_seconds() / 60
            if gap_minutes >= duration_minutes:
                slots.append({
                    "start": cursor.isoformat(),
                    "end": day_end.isoformat(),
                    "duration_minutes": int(gap_minutes),
                    "date": day.strftime("%A %Y-%m-%d"),
                })

    return slots


def _format_datetime(dt: datetime) -> dict:
    """Format a datetime for the Google Calendar API."""
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return {"date": dt.strftime("%Y-%m-%d")}
    return {"dateTime": dt.isoformat(), "timeZone": "America/New_York"}


def _parse_event(event: dict) -> dict:
    """Normalize a Google Calendar event into a simpler dict."""
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime", start.get("date", ""))
    end_str = end.get("dateTime", end.get("date", ""))

    parsed = {
        "id": event.get("id", ""),
        "summary": event.get("summary", "(no title)"),
        "start": start_str,
        "end": end_str,
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "all_day": "date" in start and "dateTime" not in start,
        "status": event.get("status", ""),
    }

    # Add parsed datetime for internal use
    try:
        parsed["start_dt"] = _parse_dt(start_str)
    except (ValueError, TypeError):
        parsed["start_dt"] = None

    return parsed


def _parse_dt(dt_str: str) -> datetime:
    """Parse an ISO datetime string, handling date-only and timezone offsets."""
    if not dt_str:
        raise ValueError("Empty datetime string")
    if len(dt_str) == 10:  # date only: YYYY-MM-DD
        return datetime.fromisoformat(dt_str)
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
