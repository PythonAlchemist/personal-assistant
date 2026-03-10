"""Daily briefing command — adaptive layout."""

from __future__ import annotations

from datetime import datetime

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

    # Week overview first
    _render_week(data["week"])

    # Then today's detail
    _render_today(data["today"])

    console.print()


def _render_week(week: dict):
    days = week["days"]
    weather = week["weather"]
    total = week["total_events"]

    console.print("[bold bright_blue]THIS WEEK[/bold bright_blue]")
    console.print("─" * 60)

    # Build a compact week view
    # Pair each day with its weather if available
    wx_by_date = {w["date"]: w for w in weather} if weather else {}

    for day in days:
        d = day["date"]
        label = day["label"]
        short = day["short_date"]
        events = day["events"]
        wx = wx_by_date.get(d, {})

        # Day header
        day_header = f"  [bold]{label}[/bold] {short}"

        # Weather snippet for this day
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

        if not events:
            console.print(f"{day_header}{wx_str}")
        else:
            console.print(f"{day_header}{wx_str}")
            for e in events:
                time_str = _event_time_short(e)
                console.print(f"    {time_str}  {e['summary']}")

    # Family dates and birthdays in the week
    if week["birthdays"]:
        console.print()
        for b in week["birthdays"]:
            console.print(f"  [bold yellow]{b['message']}[/bold yellow]")
    if week["family_dates"]:
        for fd in week["family_dates"]:
            console.print(f"  [cyan]{fd['date']}: {fd['label']}[/cyan]")

    if total == 0:
        console.print()
        console.print("  [dim]Light week — nothing on the books.[/dim]")

    console.print()


def _render_today(today: dict):
    wx = today.get("weather", {})
    events = today["events"]
    free = today["free_blocks"]
    email = today["email"]
    highlights = today["highlights"]

    console.print("[bold bright_blue]TODAY[/bold bright_blue]")
    console.print("─" * 60)

    # Weather detail
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

    # Highlights — only if there's something notable
    if highlights:
        for h in highlights:
            console.print(f"  [bold]{h}[/bold]")
        console.print()

    # Schedule
    if events:
        console.print("  [underline]Schedule[/underline]")
        for e in events:
            time_str = _event_time(e)
            loc = f"  [dim]@ {e['location']}[/dim]" if e.get("location") else ""
            multi_acct = len(set(ev.get("_account", "") for ev in events)) > 1
            acct_tag = f" [dim]({e.get('_account', '')})[/dim]" if multi_acct else ""
            console.print(f"    {time_str}  {e['summary']}{acct_tag}{loc}")

        # Free time — only show if there are events (otherwise it's obvious)
        if free and len(free) < len(events) + 2:
            console.print()
            console.print("  [underline]Open blocks[/underline]")
            for f in free:
                console.print(f"    [green]{f['start']} - {f['end']}[/green]  ({f['minutes']} min)")
        console.print()

    # Todos
    todos = today.get("todos", {})
    _render_todos(todos)

    # Email
    console.print("  [underline]Email[/underline]")
    for acct in email["accounts"]:
        unread = acct["unread"]
        if unread < 0:
            console.print(f"    [red]{acct.get('account', '?')}: error[/red]")
            continue

        style = "bold yellow" if unread > 0 else "green"
        console.print(f"    [{style}]{acct.get('account', '?')}[/{style}]: {unread} unread")

        for msg in acct["important"][:3]:
            sender = msg["from"]
            if "<" in sender:
                sender = sender.split("<")[0].strip().strip('"')
            if len(sender) > 22:
                sender = sender[:21] + "…"
            subject = msg["subject"]
            if len(subject) > 42:
                subject = subject[:41] + "…"
            console.print(f"      [dim]•[/dim] {sender}: {subject}")


def _render_todos(todos: dict):
    if not todos:
        return
    overdue = todos.get("overdue", [])
    due_soon = todos.get("due_soon", [])
    active = todos.get("active", [])

    if not active:
        return

    console.print("  [underline]Todos[/underline]")

    PRIORITY_MARKERS = {"urgent": "[bold red]!![/bold red]", "high": "[red]![/red]", "medium": "", "low": ""}

    if overdue:
        for t in overdue:
            marker = PRIORITY_MARKERS.get(t.priority.value, "")
            console.print(f"    [bold red]OVERDUE[/bold red] {marker} {t.title} [dim](due {t.due_date})[/dim]")

    for t in due_soon:
        if t in overdue:
            continue
        marker = PRIORITY_MARKERS.get(t.priority.value, "")
        from datetime import date
        delta = (t.due_date - date.today()).days
        due_label = "today" if delta == 0 else "tomorrow" if delta == 1 else f"in {delta}d"
        console.print(f"    [yellow]DUE {due_label}[/yellow] {marker} {t.title}")

    # Show other active todos (not already shown)
    shown_ids = {t.id for t in overdue + due_soon}
    others = [t for t in active if t.id not in shown_ids]
    for t in others[:5]:
        marker = PRIORITY_MARKERS.get(t.priority.value, "")
        status = "[cyan]~[/cyan] " if t.status.value == "in_progress" else "  "
        due_str = f" [dim](due {t.due_date})[/dim]" if t.due_date else ""
        console.print(f"    {status}{marker} {t.title}{due_str}")

    remaining = len(others) - 5
    if remaining > 0:
        console.print(f"    [dim]+{remaining} more[/dim]")

    console.print()


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
