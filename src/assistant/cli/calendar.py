"""Google Calendar CLI commands."""

from __future__ import annotations

from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table

from assistant import config
from assistant.services import calendar as cal_svc

console = Console()

ACCOUNT_NAMES = list(config.GOOGLE_ACCOUNTS.keys())


def _handle_cal_error(fn):
    """Decorator to catch common calendar errors."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
        except Exception as e:
            console.print(f"[red]Calendar error: {e}[/red]")
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


@click.group()
def calendar():
    """Google Calendar integration."""
    pass


@calendar.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default=None,
              help="Account to authenticate (omit to auth all)")
@_handle_cal_error
def auth(account: str | None):
    """Authenticate with Google (Calendar + Gmail)."""
    from assistant.services.google_auth import get_credentials
    accounts = [account] if account else ACCOUNT_NAMES
    for acct in accounts:
        email = config.GOOGLE_ACCOUNTS[acct]
        console.print(f"Authenticating [bold]{acct}[/bold] ({email})...")
        get_credentials(acct)
        console.print(f"[green]  {acct} authenticated![/green]")


@calendar.command()
def accounts():
    """List configured Google accounts and their auth status."""
    table = Table(title="Google Accounts")
    table.add_column("Alias", style="bold")
    table.add_column("Email")
    table.add_column("Authenticated")
    for alias, email in config.GOOGLE_ACCOUNTS.items():
        token_exists = config.google_token_path(alias).exists()
        status = "[green]yes[/green]" if token_exists else "[red]no[/red]"
        table.add_row(alias, email, status)
    console.print(table)


@calendar.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@_handle_cal_error
def calendars(account: str):
    """List available calendars."""
    cals = cal_svc.list_calendars(account)
    table = Table(title=f"Calendars — {account}")
    table.add_column("Name", style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Primary")
    for c in cals:
        primary = "✓" if c["primary"] else ""
        table.add_row(c["summary"], c["id"], primary)
    console.print(table)


@calendar.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default=None,
              help="Account (omit to show all accounts)")
@click.option("--cal", "calendar_id", default="primary", help="Calendar ID")
@_handle_cal_error
def today(account: str | None, calendar_id: str):
    """Show today's agenda."""
    accounts = [account] if account else _authenticated_accounts()
    all_events = []
    for acct in accounts:
        events = cal_svc.get_todays_agenda(calendar_id, account=acct)
        for e in events:
            e["_account"] = acct
        all_events.extend(events)

    if not all_events:
        console.print("[dim]No events today.[/dim]")
        return
    all_events.sort(key=lambda e: e.get("start", ""))
    _print_events(all_events, title=f"Today — {datetime.now().strftime('%A, %B %d')}")


@calendar.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default=None,
              help="Account (omit to show all accounts)")
@click.option("--cal", "calendar_id", default="primary", help="Calendar ID")
@_handle_cal_error
def week(account: str | None, calendar_id: str):
    """Show this week's events."""
    accounts = [account] if account else _authenticated_accounts()
    all_events = []
    for acct in accounts:
        events = cal_svc.get_week_agenda(calendar_id, account=acct)
        for e in events:
            e["_account"] = acct
        all_events.extend(events)

    if not all_events:
        console.print("[dim]No events this week.[/dim]")
        return
    all_events.sort(key=lambda e: e.get("start", ""))
    _print_events(all_events, title="This Week")


@calendar.command()
@click.argument("summary")
@click.option("--start", "-s", "start_str", required=True, help="Start time (YYYY-MM-DD or YYYY-MM-DDTHH:MM)")
@click.option("--end", "-e", "end_str", default=None, help="End time (defaults to 1 hour after start)")
@click.option("--description", "-d", default="")
@click.option("--location", "-l", default="")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@click.option("--cal", "calendar_id", default="primary")
@_handle_cal_error
def add(summary: str, start_str: str, end_str: str | None, description: str, location: str, account: str, calendar_id: str):
    """Create a new calendar event."""
    start = _parse_input_dt(start_str)
    if end_str:
        end = _parse_input_dt(end_str)
    else:
        if len(start_str) == 10:
            end = start + timedelta(days=1)
        else:
            end = start + timedelta(hours=1)

    event = cal_svc.create_event(
        summary=summary, start=start, end=end,
        description=description, location=location,
        calendar_id=calendar_id, account=account,
    )
    console.print(f"[green]Created: {event['summary']} on {event['start']} ({account})[/green]")


@calendar.command()
@click.option("--duration", "-d", default=60, help="Minimum slot duration in minutes")
@click.option("--days", default=7, help="Days to look ahead")
@click.option("--start-hour", default=9, help="Earliest hour to consider")
@click.option("--end-hour", default=17, help="Latest hour to consider")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@click.option("--cal", "calendar_id", default="primary")
@_handle_cal_error
def free(duration: int, days: int, start_hour: int, end_hour: int, account: str, calendar_id: str):
    """Find free time slots in your calendar."""
    slots = cal_svc.find_free_slots(
        duration_minutes=duration, days_ahead=days,
        start_hour=start_hour, end_hour=end_hour,
        calendar_id=calendar_id, account=account,
    )
    if not slots:
        console.print(f"[dim]No free slots of {duration}+ minutes found in the next {days} days.[/dim]")
        return

    table = Table(title=f"Free Slots ({duration}+ min)")
    table.add_column("Day", style="bold")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Duration")
    for s in slots:
        start_dt = datetime.fromisoformat(s["start"])
        end_dt = datetime.fromisoformat(s["end"])
        table.add_row(s["date"], start_dt.strftime("%H:%M"), end_dt.strftime("%H:%M"), f"{s['duration_minutes']} min")
    console.print(table)


@calendar.command("delete")
@click.argument("event_id")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@click.option("--cal", "calendar_id", default="primary")
@click.confirmation_option(prompt="Are you sure you want to delete this event?")
@_handle_cal_error
def delete_event(event_id: str, account: str, calendar_id: str):
    """Delete a calendar event by ID."""
    cal_svc.delete_event(event_id, calendar_id, account=account)
    console.print("[green]Event deleted.[/green]")


def _authenticated_accounts() -> list[str]:
    """Return list of accounts that have tokens."""
    return [alias for alias in ACCOUNT_NAMES if config.google_token_path(alias).exists()]


def _print_events(events: list[dict], title: str = "Events"):
    """Pretty-print a list of events."""
    show_account = len(set(e.get("_account", "") for e in events)) > 1
    table = Table(title=title)
    table.add_column("Time", style="bold", width=20)
    table.add_column("Event")
    if show_account:
        table.add_column("Account", style="cyan")
    table.add_column("Location", style="dim")

    current_date = None
    for e in events:
        if e.get("start_dt"):
            event_date = e["start_dt"].strftime("%Y-%m-%d")
            if event_date != current_date:
                if current_date is not None:
                    table.add_section()
                current_date = event_date

        if e["all_day"]:
            time_str = "All day"
        else:
            try:
                start_dt = datetime.fromisoformat(e["start"].replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(e["end"].replace("Z", "+00:00"))
                time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
            except (ValueError, TypeError):
                time_str = e["start"]

        row = [time_str, e["summary"]]
        if show_account:
            row.append(e.get("_account", ""))
        row.append(e.get("location", ""))
        table.add_row(*row)

    console.print(table)


def _parse_input_dt(s: str) -> datetime:
    """Parse user-provided datetime string."""
    return datetime.fromisoformat(s)
