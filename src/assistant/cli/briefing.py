"""Daily briefing command — adaptive layout."""

from __future__ import annotations

from datetime import date, datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from assistant.services.briefing import generate_briefing

console = Console()


@click.command()
def briefing():
    """Show your daily briefing."""
    console.print()
    data = generate_briefing()

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    console.print(Panel(
        f"[bold white]{data['date']}[/bold white]",
        title=f"[bold]{greeting}[/bold]",
        border_style="bright_blue",
        padding=(0, 2),
    ))
    console.print()

    week = data["week"]
    today = data["today"]

    _render_today(today)
    _render_week(week)
    _render_weekend(week)
    _render_local_events(today.get("local_events", {}))
    _render_todos(today.get("todos", {}))
    _render_email(today["email"])

    console.print()


def _render_today(today: dict):
    wx = today.get("weather", {})
    events = today["events"]
    free = today["free_blocks"]

    console.print("[bold bright_blue]TODAY[/bold bright_blue]")
    console.print("─" * 60)

    # Weather
    if wx and not wx.get("error"):
        cur = wx.get("current", {})
        td = wx.get("today", {})
        if cur:
            temp = cur.get("temp", "?")
            feels = cur.get("feels_like", "?")
            condition = cur.get("condition", "")
            wind = cur.get("wind_speed", "?")
            console.print(f"  {temp}°F, {condition.lower()}. Feels like {feels}°F, wind {wind} mph.")
            if td:
                high = td.get("high", "?")
                low = td.get("low", "?")
                precip = td.get("precip_chance", 0)
                if precip and precip > 10:
                    console.print(f"  High {high}°F / Low {low}°F — [cyan]{precip}% chance of rain[/cyan]")
                else:
                    console.print(f"  High {high}°F / Low {low}°F")
        console.print()

    # Calendar
    if events:
        console.print("  [underline]Schedule[/underline]")
        for e in events:
            time_str = _event_time(e)
            loc = f"  [dim]@ {e['location']}[/dim]" if e.get("location") else ""
            multi_acct = len(set(ev.get("_account", "") for ev in events)) > 1
            acct_tag = f" [dim]({e.get('_account', '')})[/dim]" if multi_acct else ""
            console.print(f"    {time_str}  {e['summary']}{acct_tag}{loc}")

        if free and len(free) < len(events) + 2:
            console.print()
            console.print("  [underline]Open blocks[/underline]")
            for f in free:
                console.print(f"    [green]{f['start']} - {f['end']}[/green]  ({f['minutes']} min)")
    else:
        console.print("  [dim]No events — open schedule[/dim]")

    console.print()


def _render_week(week: dict):
    days = week["days"]
    weather = week["weather"]
    wx_by_date = {w["date"]: w for w in weather} if weather else {}

    # Skip today (index 0), show weekdays only (Mon-Fri)
    weekdays = [d for d in days[1:] if _parse_date(d["date"]).weekday() < 5]

    if not weekdays:
        return

    console.print("[bold bright_blue]THIS WEEK[/bold bright_blue]")
    console.print("─" * 60)

    for day in weekdays:
        _render_day_row(day, wx_by_date)

    # Family dates and birthdays
    if week["birthdays"]:
        console.print()
        for b in week["birthdays"]:
            console.print(f"  [bold yellow]{b['message']}[/bold yellow]")
    if week["family_dates"]:
        for fd in week["family_dates"]:
            console.print(f"  [cyan]{fd['date']}: {fd['label']}[/cyan]")

    has_events = any(d["event_count"] > 0 for d in weekdays)
    if not has_events:
        console.print()
        console.print("  [dim]Clear week ahead.[/dim]")

    console.print()


def _render_weekend(week: dict):
    days = week["days"]
    weather = week["weather"]
    wx_by_date = {w["date"]: w for w in weather} if weather else {}

    weekend_days = [d for d in days[1:] if _parse_date(d["date"]).weekday() >= 5]

    if not weekend_days:
        return

    console.print("[bold bright_blue]WEEKEND[/bold bright_blue]")
    console.print("─" * 60)

    for day in weekend_days:
        _render_day_row(day, wx_by_date)

    has_events = any(d["event_count"] > 0 for d in weekend_days)
    if not has_events:
        console.print()
        console.print("  [dim]Nothing planned — wide open.[/dim]")

    console.print()


def _render_day_row(day: dict, wx_by_date: dict):
    d = day["date"]
    label = day["label"]
    short = day["short_date"]
    events = day["events"]
    wx = wx_by_date.get(d, {})

    day_header = f"  [bold]{label}[/bold] {short}"

    wx_bits = []
    if wx:
        wx_bits.append(f"{wx.get('low', '')}–{wx.get('high', '')}°F")
        cond = wx.get("condition", "")
        if cond and cond not in ("Clear sky", "Mainly clear"):
            wx_bits.append(cond.lower())
        precip = wx.get("precip_chance", 0)
        if precip and precip > 20:
            wx_bits.append(f"{precip}% rain")
    wx_str = f"  [dim]({', '.join(wx_bits)})[/dim]" if wx_bits else ""

    console.print(f"{day_header}{wx_str}")
    for e in events:
        time_str = _event_time_short(e)
        console.print(f"    {time_str}  {e['summary']}")


def _render_todos(todos: dict):
    if not todos:
        return

    from assistant.services.todoist import task_priority_label, task_due_date

    overdue = todos.get("overdue", [])
    due_soon = todos.get("due_soon", [])
    this_week = todos.get("this_week", [])
    untriaged = todos.get("untriaged", [])

    if not overdue and not due_soon and not this_week and not untriaged:
        return

    PRIORITY_MARKERS = {"urgent": "[bold red]!![/bold red]", "high": "[red]![/red]", "medium": "", "normal": ""}

    console.print("[bold bright_blue]TODOS[/bold bright_blue]")
    console.print("─" * 60)

    # Due today and overdue — most important, shown first
    overdue_ids = {t["id"] for t in overdue}
    due_today = [t for t in due_soon if t["id"] not in overdue_ids and task_due_date(t) == date.today()]
    due_tomorrow = [t for t in due_soon if t["id"] not in overdue_ids and task_due_date(t) and task_due_date(t) != date.today()]

    if overdue or due_today:
        console.print("  [underline]Due Today[/underline]")
        for t in overdue:
            marker = PRIORITY_MARKERS.get(task_priority_label(t), "")
            due = task_due_date(t)
            console.print(f"    [bold red]OVERDUE[/bold red] {marker} {t['content']} [dim](due {due})[/dim]")
        for t in due_today:
            marker = PRIORITY_MARKERS.get(task_priority_label(t), "")
            console.print(f"    {marker} {t['content']}")
        console.print()

    if due_tomorrow:
        console.print("  [underline]Due Soon[/underline]")
        for t in due_tomorrow:
            marker = PRIORITY_MARKERS.get(task_priority_label(t), "")
            due = task_due_date(t)
            delta = (due - date.today()).days if due else 0
            due_label = "tomorrow" if delta == 1 else f"in {delta}d"
            console.print(f"    [yellow]{due_label}[/yellow] {marker} {t['content']}")
        console.print()

    # This Week
    shown_ids = overdue_ids | {t["id"] for t in due_soon}
    week_tasks = [t for t in this_week if t["id"] not in shown_ids]
    if week_tasks:
        console.print("  [underline]This Week[/underline]")
        for t in week_tasks:
            marker = PRIORITY_MARKERS.get(task_priority_label(t), "")
            console.print(f"    {marker} {t['content']}")
        console.print()

    # Needs triage
    if untriaged:
        console.print(f"  [underline]Needs Triage ({len(untriaged)})[/underline]")
        for t in untriaged:
            due = task_due_date(t)
            due_str = f" [dim](due {due})[/dim]" if due else ""
            marker = PRIORITY_MARKERS.get(task_priority_label(t), "")
            console.print(f"    [magenta]?[/magenta] {marker} {t['content']}{due_str}")
        console.print()


def _render_local_events(local_events: dict):
    today_events = local_events.get("today", [])
    weekend_events = local_events.get("weekend", [])
    week_events = local_events.get("week", [])

    # Exclude weekend events from the "week" list to avoid duplication
    weekend_ids = {e["id"] for e in weekend_events}
    weekday_events = [e for e in week_events if e["id"] not in weekend_ids]

    if not today_events and not weekend_events and not weekday_events:
        return

    console.print("[bold bright_blue]LOCAL EVENTS[/bold bright_blue]")
    console.print("─" * 60)

    if today_events:
        console.print("  [underline]Today[/underline]")
        _render_events_table(today_events)
        console.print()

    if weekend_events:
        console.print("  [underline]This Weekend[/underline]")
        _render_events_table(weekend_events)
        console.print()

    if weekday_events:
        console.print("  [underline]This Week[/underline]")
        _render_events_table(weekday_events[:8])
        remaining = len(weekday_events) - 8
        if remaining > 0:
            console.print(f"  [dim]+{remaining} more[/dim]")
        console.print()


def _render_events_table(events: list[dict]):
    import re

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1), pad_edge=False)
    table.add_column("When", style="cyan", no_wrap=True, min_width=17)
    table.add_column("Event", no_wrap=False)
    table.add_column("Where", style="dim", max_width=24)
    table.add_column("Tags", style="dim", max_width=18)

    for e in events:
        d = _parse_date(e["start_date"])
        day = d.strftime("%a %d")
        time_str = e.get("start_time") or "all day"
        when = f"{day} {time_str}"

        title = e.get("title", "")
        if len(title) > 35:
            title = title[:34] + "…"

        # One-line description snippet
        desc = re.sub(r"<[^>]+>", "", (e.get("description") or "")).strip()
        desc = re.sub(r"\s+", " ", desc)
        if len(desc) > 50:
            desc = desc[:49] + "…"
        if desc:
            title = f"{title}\n[dim italic]{desc}[/dim italic]"

        # URL — prefer event-specific URL, fall back to source page
        from assistant.config import LOCAL_EVENT_SOURCE_URLS
        url = e.get("url", "")
        if not url or not url.startswith("http"):
            url = LOCAL_EVENT_SOURCE_URLS.get(e.get("source", ""), "")
        if url:
            title = f"{title}\n[link={url}][blue underline]link[/blue underline][/link]"

        # Location
        location = (e.get("location") or "").strip()
        if len(location) > 24:
            location = location[:23] + "…"

        # Categories — pick first 2 meaningful ones, skip audience/language tags
        cats = e.get("categories", "")
        if cats:
            skip = {"english", "spanish", "adults", "older adults", "new adults (18-24)",
                    "high school", "middle school", "parents/caregivers",
                    "homeschool", "teens (12-18)", "preteens (10-12)",
                    "school age (5-11)", "preschool (3-5)", "babies (0-2)",
                    "toddlers (2-3)"}
            cat_list = [c.strip() for c in cats.split(",")
                        if c.strip().lower() not in skip][:2]
            cats = ", ".join(cat_list)

        table.add_row(when, title, location, cats)

    console.print(table)


def _render_email(email: dict):
    console.print("[bold bright_blue]EMAIL[/bold bright_blue]")
    console.print("─" * 60)
    for acct in email["accounts"]:
        unread = acct["unread"]
        if unread < 0:
            console.print(f"  [red]{acct.get('account', '?')}: error[/red]")
            continue

        style = "bold yellow" if unread > 0 else "green"
        console.print(f"  [{style}]{acct.get('account', '?')}[/{style}]: {unread} unread")

        for msg in acct["important"][:3]:
            sender = msg["from"]
            if "<" in sender:
                sender = sender.split("<")[0].strip().strip('"')
            if len(sender) > 22:
                sender = sender[:21] + "…"
            subject = msg["subject"]
            if len(subject) > 42:
                subject = subject[:41] + "…"
            console.print(f"    [dim]•[/dim] {sender}: {subject}")

    console.print()


def _parse_date(date_str: str) -> date:
    return date.fromisoformat(date_str)


def _event_time(event: dict) -> str:
    if event.get("all_day"):
        return "[dim]all day[/dim]   "
    try:
        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(event["end"].replace("Z", "+00:00"))
        return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
    except (ValueError, TypeError):
        return event.get("start", "")[:10]


def _event_time_short(event: dict) -> str:
    if event.get("all_day"):
        return "[dim]all day[/dim]"
    try:
        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
        return f"[dim]{start.strftime('%H:%M')}[/dim]"
    except (ValueError, TypeError):
        return ""
