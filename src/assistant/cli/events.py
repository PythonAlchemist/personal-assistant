"""Local events commands."""

from __future__ import annotations

import click
from rich.console import Console

from assistant.services import local_events as events_svc

console = Console()


@click.group()
def events():
    """Browse and manage local event feeds."""
    pass


@events.command()
def refresh():
    """Fetch latest events from all configured feeds."""
    console.print("[dim]Refreshing local event feeds...[/dim]")
    results = events_svc.refresh_all_feeds()
    for source, count in results.items():
        if count < 0:
            console.print(f"  [red]{source}: error[/red]")
        else:
            console.print(f"  [green]{source}: {count} events[/green]")
    total = sum(c for c in results.values() if c > 0)
    console.print(f"\n[bold]{total} events cached.[/bold]")


@events.command(name="list")
@click.option("--days", default=7, help="Number of days ahead to show.")
def list_events(days):
    """Show upcoming local events."""
    from datetime import date, timedelta

    start = date.today().isoformat()
    end = (date.today() + timedelta(days=days)).isoformat()
    results = events_svc.get_events_between(start, end)

    if not results:
        console.print("[dim]No events found. Try 'assistant events refresh' first.[/dim]")
        return

    console.print(f"[bold]Local events — next {days} days[/bold]\n")
    for e in results:
        time_str = f" {e['start_time']}" if e.get("start_time") else ""
        loc = f"  [dim]@ {e['location']}[/dim]" if e.get("location") else ""
        cat = f"  [dim][{e['categories']}][/dim]" if e.get("categories") else ""
        console.print(f"  {e['start_date']}{time_str}  {e['title']}{loc}{cat}")
