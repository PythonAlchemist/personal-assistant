"""Family data management commands."""

from __future__ import annotations

from datetime import date

import click
from rich.console import Console
from rich.table import Table

from assistant.services import family as family_svc

console = Console()


@click.group()
def family():
    """Manage family members, dates, and notes."""
    pass


@family.command()
@click.argument("name")
@click.option("--relationship", "-r", type=click.Choice(["self", "spouse", "child", "other"]), required=True)
@click.option("--birthday", "-b", type=click.DateTime(formats=["%Y-%m-%d"]), default=None)
def add(name: str, relationship: str, birthday):
    """Add a family member."""
    bday = birthday.date() if birthday else None
    member = family_svc.add_family_member(name, relationship, bday)
    console.print(f"[green]Added {member.name} ({member.relationship.value})[/green]")


@family.command("list")
def list_members():
    """List all family members."""
    members = family_svc.list_family()
    if not members:
        console.print("[dim]No family members yet. Use 'assistant family add' to get started.[/dim]")
        return
    table = Table(title="Family")
    table.add_column("Name", style="bold")
    table.add_column("Relationship")
    table.add_column("Birthday")
    for m in members:
        table.add_row(m.name, m.relationship.value, str(m.birthday) if m.birthday else "—")
    console.print(table)


@family.command()
@click.argument("name")
def show(name: str):
    """Show details for a family member."""
    from assistant.storage import family_repo
    from assistant.storage.database import get_connection, init_db
    from assistant import config

    conn = get_connection(config.DB_PATH)
    init_db(conn)
    member = family_repo.get_member_by_name(conn, name)
    if not member:
        console.print(f"[red]No member found with name '{name}'[/red]")
        return

    console.print(f"[bold]{member.name}[/bold] — {member.relationship.value}")
    if member.birthday:
        console.print(f"  Birthday: {member.birthday}")
    if member.preferences:
        console.print("  Preferences:")
        for k, v in member.preferences.items():
            console.print(f"    {k}: {v}")

    dates = family_repo.list_dates(conn, member.id)
    if dates:
        console.print("  Important dates:")
        for d in dates:
            console.print(f"    {d.date}: {d.label}")

    notes = family_repo.list_notes(conn, member.id)
    if notes:
        console.print("  Notes:")
        for n in notes:
            console.print(f"    - {n.content}")


@family.command("add-date")
@click.argument("label")
@click.option("--date", "-d", "dt", type=click.DateTime(formats=["%Y-%m-%d"]), required=True)
@click.option("--member", "-m", default=None, help="Associate with a family member")
@click.option("--yearly/--no-yearly", default=False, help="Recurs every year")
@click.option("--notes", "-n", default="")
def add_date(label: str, dt, member: str | None, yearly: bool, notes: str):
    """Add an important date."""
    imp = family_svc.add_important_date(label, dt.date(), member, yearly, notes)
    console.print(f"[green]Added date: {imp.label} on {imp.date}[/green]")


@family.command()
@click.argument("content")
@click.option("--member", "-m", default=None, help="Associate with a family member")
@click.option("--tags", "-t", default="", help="Comma-separated tags")
def note(content: str, member: str | None, tags: str):
    """Add a note."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    n = family_svc.add_note(content, member, tag_list)
    console.print(f"[green]Note added (#{n.id})[/green]")


@family.command()
@click.option("--days", "-d", default=30, help="Number of days to look ahead")
def upcoming(days: int):
    """Show upcoming dates and birthdays."""
    dates = family_svc.get_upcoming(days)
    members = family_svc.list_family()
    today = date.today()

    # Also check member birthdays
    for m in members:
        if m.birthday:
            this_year = m.birthday.replace(year=today.year)
            if this_year < today:
                this_year = this_year.replace(year=today.year + 1)
            delta = (this_year - today).days
            if 0 <= delta <= days:
                console.print(f"  🎂 {this_year}: {m.name}'s birthday")

    if dates:
        for d in dates:
            console.print(f"  📅 {d.date}: {d.label}")
    elif not any(m.birthday for m in members):
        console.print("[dim]No upcoming dates.[/dim]")
