"""Briefings — weekly overview + daily detail, adaptive format."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from assistant import config
from assistant.services import calendar as cal_svc
from assistant.services import gmail as gmail_svc
from assistant.services import family as family_svc
from assistant.services import weather as weather_svc
from assistant.services import todoist as todoist_svc
from assistant.services import local_events as events_svc


def generate_briefing() -> dict:
    """Build a full briefing: week-at-a-glance then today's detail."""
    today = date.today()
    return {
        "date": today.strftime("%A, %B %d, %Y"),
        "week": _get_week_overview(today),
        "today": _get_today_detail(today),
    }


def _get_week_overview(today: date) -> dict:
    """High-level view of the week ahead."""
    accounts = _authenticated_accounts()

    # Calendar: next 7 days grouped by day
    week_start = datetime(today.year, today.month, today.day)
    week_end = week_start + timedelta(days=7)
    week_events = {}
    for acct in accounts:
        try:
            events = cal_svc.list_events(week_start, week_end, account=acct)
            for e in events:
                e["_account"] = acct
                # Group by date
                event_date = e.get("start", "")[:10]
                week_events.setdefault(event_date, []).append(e)
        except Exception:
            pass

    days = []
    for i in range(7):
        d = today + timedelta(days=i)
        ds = d.isoformat()
        day_events = week_events.get(ds, [])
        day_events.sort(key=lambda e: e.get("start", ""))
        days.append({
            "date": ds,
            "label": d.strftime("%A") if i > 0 else "Today",
            "short_date": d.strftime("%b %d"),
            "events": day_events,
            "event_count": len(day_events),
        })

    # Weather forecast for the week
    weather_forecast = []
    try:
        wx = weather_svc.get_current_and_forecast()
        weather_forecast = wx.get("forecast", [])[:7]
    except Exception:
        pass

    # Family dates in next 7 days
    family_dates = family_svc.get_upcoming(days=7)
    birthdays = _get_birthdays(today, days=7)

    # Busy-ness score: helps vary the format
    total_events = sum(d["event_count"] for d in days)
    busiest_day = max(days, key=lambda d: d["event_count"]) if days else None

    return {
        "days": days,
        "weather": weather_forecast,
        "family_dates": [{"date": str(d.date), "label": d.label} for d in family_dates],
        "birthdays": birthdays,
        "total_events": total_events,
        "busiest_day": busiest_day,
    }


def _get_today_detail(today: date) -> dict:
    """Detailed view of today: weather, schedule, email."""
    accounts = _authenticated_accounts()

    # Weather
    weather = {}
    try:
        weather = weather_svc.get_today_summary()
    except Exception as e:
        weather = {"error": str(e)}

    # Today's events (already sorted)
    today_events = []
    for acct in accounts:
        try:
            events = cal_svc.get_todays_agenda(account=acct)
            for e in events:
                e["_account"] = acct
            today_events.extend(events)
        except Exception:
            pass
    today_events.sort(key=lambda e: e.get("start", ""))

    # Free time analysis
    free_blocks = _analyze_free_time(today_events)

    # Email
    email = _get_email_section()

    # Todos (from Todoist)
    try:
        todos_overdue = todoist_svc.get_overdue()
        todos_due_soon = todoist_svc.get_due_soon(days=3)
        todos_this_week = todoist_svc.get_this_week()
        todos_active = todoist_svc.get_active_tasks()
        todos_untriaged = todoist_svc.get_untriaged()
    except Exception:
        todos_overdue = []
        todos_due_soon = []
        todos_this_week = []
        todos_active = []
        todos_untriaged = []

    # Auto-refresh local event feeds if stale
    try:
        if events_svc.feeds_are_stale():
            events_svc.refresh_all_feeds()
    except Exception:
        pass

    # Local events (from cached feeds)
    local_events_today = []
    local_events_week = []
    local_events_weekend = []
    try:
        local_events_today = events_svc.get_events_between(
            today.isoformat(), today.isoformat()
        )
        week_end = today + timedelta(days=7)
        local_events_week = events_svc.get_events_between(
            (today + timedelta(days=1)).isoformat(), week_end.isoformat()
        )
        # Split weekend events out
        weekend_dates = set()
        for i in range(7):
            d = today + timedelta(days=i)
            if d.weekday() >= 5:
                weekend_dates.add(d.isoformat())
        local_events_weekend = [
            e for e in local_events_week if e["start_date"] in weekend_dates
        ]
    except Exception:
        pass

    # What's different about today
    highlights = []
    birthdays = _get_birthdays(today, days=0)
    for b in birthdays:
        highlights.append(b["message"])

    if not today_events:
        highlights.append("No events — open schedule")
    elif len(today_events) >= 5:
        highlights.append(f"Busy day — {len(today_events)} events")

    if todos_overdue:
        highlights.append(f"{len(todos_overdue)} overdue todo{'s' if len(todos_overdue) != 1 else ''}")
    if todos_untriaged:
        highlights.append(f"{len(todos_untriaged)} inbox item{'s' if len(todos_untriaged) != 1 else ''} need triage")
    if local_events_today:
        highlights.append(f"{len(local_events_today)} local event{'s' if len(local_events_today) != 1 else ''} today")

    return {
        "weather": weather,
        "events": today_events,
        "free_blocks": free_blocks,
        "email": email,
        "todos": {
            "overdue": todos_overdue,
            "due_soon": todos_due_soon,
            "this_week": todos_this_week,
            "active": todos_active,
            "untriaged": todos_untriaged,
        },
        "local_events": {
            "today": local_events_today,
            "week": local_events_week,
            "weekend": local_events_weekend,
        },
        "highlights": highlights,
    }


def _get_email_section() -> dict:
    """Get unread counts and important recent emails."""
    accounts = _authenticated_accounts()
    account_summaries = []

    for acct in accounts:
        try:
            unread = gmail_svc.get_unread_count(acct)
            recent = []
            if unread > 0:
                messages = gmail_svc.list_messages(
                    acct, query="is:unread in:inbox -category:promotions -category:social",
                    max_results=5,
                )
                recent = [
                    {"from": m["from"], "subject": m["subject"], "snippet": m["snippet"]}
                    for m in messages
                ]
            account_summaries.append({
                "account": acct,
                "email": config.GOOGLE_ACCOUNTS.get(acct, acct),
                "unread": unread,
                "important": recent,
            })
        except Exception as e:
            account_summaries.append({
                "account": acct,
                "unread": -1,
                "important": [],
                "error": str(e),
            })

    return {"accounts": account_summaries}


def _get_birthdays(today: date, days: int = 7) -> list[dict]:
    """Check family member birthdays within N days. days=0 means today only."""
    members = family_svc.list_family()
    birthdays = []
    for m in members:
        if not m.birthday:
            continue
        this_year = m.birthday.replace(year=today.year)
        if this_year < today:
            this_year = this_year.replace(year=today.year + 1)
        delta = (this_year - today).days
        if delta == 0:
            birthdays.append({"name": m.name, "date": str(this_year), "message": f"{m.name}'s birthday is TODAY!"})
        elif 0 < delta <= days:
            birthdays.append({"name": m.name, "date": str(this_year), "message": f"{m.name}'s birthday in {delta} days ({this_year.strftime('%A, %b %d')})"})
    return birthdays


def _analyze_free_time(events: list[dict]) -> list[dict]:
    """Find gaps in today's schedule."""
    if not events:
        return [{"label": "Full day open", "start": "09:00", "end": "17:00", "minutes": 480}]

    blocks = []
    now = datetime.now()
    day_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    day_end = now.replace(hour=17, minute=0, second=0, microsecond=0)
    cursor = max(day_start, now) if now.date() == date.today() else day_start

    for e in events:
        if e.get("all_day"):
            continue
        try:
            evt_start = datetime.fromisoformat(e["start"].replace("Z", "+00:00")).replace(tzinfo=None)
            evt_end = datetime.fromisoformat(e["end"].replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue

        if evt_start > cursor:
            gap = int((evt_start - cursor).total_seconds() / 60)
            if gap >= 30:
                blocks.append({
                    "start": cursor.strftime("%H:%M"),
                    "end": evt_start.strftime("%H:%M"),
                    "minutes": gap,
                    "label": f"{gap} min free",
                })
        cursor = max(cursor, evt_end)

    if cursor < day_end:
        gap = int((day_end - cursor).total_seconds() / 60)
        if gap >= 30:
            blocks.append({
                "start": cursor.strftime("%H:%M"),
                "end": day_end.strftime("%H:%M"),
                "minutes": gap,
                "label": f"{gap} min free",
            })

    return blocks


def _authenticated_accounts() -> list[str]:
    return [alias for alias in config.GOOGLE_ACCOUNTS if config.google_token_path(alias).exists()]
