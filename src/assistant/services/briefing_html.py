"""HTML rendering for the daily briefing email."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


# ---------------------------------------------------------------------------
# Template helper functions
# ---------------------------------------------------------------------------

def _format_event_time(event: dict) -> str:
    """Return 'HH:MM - HH:MM' or 'all day'."""
    if event.get("all_day"):
        return "all day"
    try:
        start = _parse_dt(event.get("start", ""))
        end = _parse_dt(event.get("end", ""))
        if start and end:
            return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        if start:
            return start.strftime("%H:%M")
    except Exception:
        pass
    return ""


def _format_event_time_short(event: dict) -> str:
    """Return 'HH:MM' or 'all day'."""
    if event.get("all_day"):
        return "all day"
    try:
        start = _parse_dt(event.get("start", ""))
        if start:
            return start.strftime("%H:%M")
    except Exception:
        pass
    return ""


def _format_local_event_when(event: dict) -> str:
    """Return 'Mon 30 6:30pm' style string."""
    try:
        d = date.fromisoformat(event["start_date"])
        label = d.strftime("%a %-d")
        t = event.get("start_time", "")
        if t:
            # Parse HH:MM or HH:MM:SS
            parts = t.split(":")
            h, m = int(parts[0]), int(parts[1])
            suffix = "am" if h < 12 else "pm"
            h12 = h % 12 or 12
            if m:
                return f"{label} {h12}:{m:02d}{suffix}"
            return f"{label} {h12}{suffix}"
        return label
    except Exception:
        return str(event.get("start_date", ""))


def _format_due_delta(task: dict) -> str:
    """Return 'tomorrow', 'in 3d', etc. relative to today."""
    d = _task_due_date(task)
    if d is None:
        return ""
    today = date.today()
    delta = (d - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta > 1:
        return f"in {delta}d"
    return f"{abs(delta)}d ago"


def _task_due_date(task: dict) -> date | None:
    """Extract due date from a Todoist task dict."""
    due = task.get("due")
    if not due:
        return None
    raw = due.get("date") if isinstance(due, dict) else None
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _parse_dt(value: str) -> datetime | None:
    """Parse an ISO datetime string, stripping timezone info."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Data processing helpers
# ---------------------------------------------------------------------------

def _split_week_days(days: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split non-today week days into (weekdays, weekend_days)."""
    weekdays = []
    weekend = []
    for day in days[1:]:  # skip index 0 = today
        try:
            d = date.fromisoformat(day["date"])
            if d.weekday() >= 5:
                weekend.append(day)
            else:
                weekdays.append(day)
        except (ValueError, KeyError):
            weekdays.append(day)
    return weekdays, weekend


def _build_wx_by_date(weather_list: list[dict]) -> dict[str, dict]:
    """Build a date-string -> weather-dict lookup from week weather forecast."""
    return {w["date"]: w for w in weather_list if "date" in w}


def _split_todos(todos_dict: dict) -> tuple[list, list, list, list, list]:
    """
    Return (overdue, due_today, due_soon, this_week, untriaged).

    The briefing service produces:
        {"overdue": [...], "due_soon": [...], "this_week": [...],
         "active": [...], "untriaged": [...]}

    We derive due_today from due_soon (tasks where due.date == today).
    """
    today = date.today()
    today_str = today.isoformat()

    overdue = todos_dict.get("overdue", [])
    due_soon_raw = todos_dict.get("due_soon", [])
    this_week = todos_dict.get("this_week", [])
    untriaged = todos_dict.get("untriaged", [])

    due_today = []
    due_soon = []
    for task in due_soon_raw:
        d = _task_due_date(task)
        if d and d.isoformat() == today_str:
            due_today.append(task)
        else:
            due_soon.append(task)

    return overdue, due_today, due_soon, this_week, untriaged


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    if hour < 17:
        return "Good Afternoon"
    return "Good Evening"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_html(data: dict) -> str:
    """Render the briefing data dict to an HTML string."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    # Register helper functions as globals
    env.globals["format_event_time"] = _format_event_time
    env.globals["format_event_time_short"] = _format_event_time_short
    env.globals["format_local_event_when"] = _format_local_event_when
    env.globals["format_due_delta"] = _format_due_delta
    env.globals["task_due_date"] = _task_due_date

    template = env.get_template("briefing.html")

    week = data.get("week", {})
    today_data = data.get("today", {})
    days = week.get("days", [])

    week_weekdays, weekend_days = _split_week_days(days)
    wx_by_date = _build_wx_by_date(week.get("weather", []))

    local = today_data.get("local_events", {})
    local_events_today = local.get("today", [])
    local_events_weekend = local.get("weekend", [])
    # "week" bucket = non-today, non-weekend weekday local events
    local_events_weekday = [
        e for e in local.get("week", [])
        if e not in local_events_weekend
    ]

    todos_dict = today_data.get("todos", {})
    todos_overdue, todos_due_today, todos_due_soon, todos_this_week, todos_untriaged = _split_todos(todos_dict)

    has_todos = bool(
        todos_overdue or todos_due_today or todos_due_soon
        or todos_this_week or todos_untriaged
    )

    context = {
        "greeting": _greeting(),
        "date": data.get("date", ""),
        "today": today_data,
        "week_weekdays": week_weekdays,
        "weekend_days": weekend_days,
        "wx_by_date": wx_by_date,
        "local_events_today": local_events_today,
        "local_events_weekend": local_events_weekend,
        "local_events_weekday": local_events_weekday,
        "todos_overdue": todos_overdue,
        "todos_due_today": todos_due_today,
        "todos_due_soon": todos_due_soon,
        "todos_this_week": todos_this_week,
        "todos_untriaged": todos_untriaged,
        "has_todos": has_todos,
    }

    return template.render(**context)
