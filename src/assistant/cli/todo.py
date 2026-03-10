"""Todo list CLI commands."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from assistant.services import todo as todo_svc

console = Console()

PRIORITY_STYLES = {
    "urgent": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim",
}

STATUS_ICONS = {
    "todo": "[ ]",
    "in_progress": "[~]",
    "done": "[x]",
}


@click.group()
def todo():
    """Manage your todo list."""
    pass


@todo.command()
@click.argument("title")
@click.option("--due", "-d", type=click.DateTime(formats=["%Y-%m-%d"]), default=None)
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "urgent"]), default="medium")
@click.option("--description", "-D", default="")
@click.option("--tags", "-t", default="", help="Comma-separated tags")
def add(title: str, due, priority: str, description: str, tags: str):
    """Add a todo."""
    due_date = due.date() if due else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    t = todo_svc.add(title, due=due_date, priority=priority, description=description, tags=tag_list)
    console.print(f"[green]Added #{t.id}: {t.title}[/green]")


@todo.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Include completed todos")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "urgent"]), default=None)
def list_todos(show_all: bool, priority: str | None):
    """List todos."""
    todos = todo_svc.list_all(include_done=show_all, priority=priority)
    if not todos:
        console.print("[dim]No todos. Use 'assistant todo add' to create one.[/dim]")
        return
    _print_todos(todos)


@todo.command()
@click.argument("todo_id", type=int)
def done(todo_id: int):
    """Mark a todo as complete."""
    t = todo_svc.complete(todo_id)
    if t:
        console.print(f"[green]Completed: {t.title}[/green]")
    else:
        console.print(f"[red]Todo #{todo_id} not found.[/red]")


@todo.command()
@click.argument("todo_id", type=int)
def start(todo_id: int):
    """Mark a todo as in progress."""
    t = todo_svc.start(todo_id)
    if t:
        console.print(f"[cyan]Started: {t.title}[/cyan]")
    else:
        console.print(f"[red]Todo #{todo_id} not found.[/red]")


@todo.command()
@click.argument("todo_id", type=int)
@click.confirmation_option(prompt="Delete this todo?")
def rm(todo_id: int):
    """Delete a todo."""
    if todo_svc.remove(todo_id):
        console.print(f"[green]Deleted #{todo_id}.[/green]")
    else:
        console.print(f"[red]Todo #{todo_id} not found.[/red]")


@todo.command()
@click.argument("todo_id", type=int)
@click.option("--title", "-T", default=None)
@click.option("--due", "-d", type=click.DateTime(formats=["%Y-%m-%d"]), default=None)
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "urgent"]), default=None)
@click.option("--description", "-D", default=None)
def edit(todo_id: int, title: str | None, due, priority: str | None, description: str | None):
    """Edit a todo."""
    due_date = due.date() if due else None
    t = todo_svc.update(todo_id, title=title, due=due_date, priority=priority, description=description)
    if t:
        console.print(f"[green]Updated #{t.id}: {t.title}[/green]")
    else:
        console.print(f"[red]Todo #{todo_id} not found.[/red]")


@todo.command()
def overdue():
    """Show overdue todos."""
    todos = todo_svc.overdue()
    if not todos:
        console.print("[green]Nothing overdue.[/green]")
        return
    console.print(f"[bold red]{len(todos)} overdue:[/bold red]")
    _print_todos(todos)


def _print_todos(todos: list):
    from datetime import date
    today = date.today()

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("", width=3)
    table.add_column("Todo")
    table.add_column("Priority", width=8)
    table.add_column("Due", width=12)

    for t in todos:
        icon = STATUS_ICONS.get(t.status.value, "[ ]")
        if t.status.value == "done":
            icon = f"[green]{icon}[/green]"
        elif t.status.value == "in_progress":
            icon = f"[cyan]{icon}[/cyan]"

        pri_style = PRIORITY_STYLES.get(t.priority.value, "")
        pri_label = f"[{pri_style}]{t.priority.value}[/{pri_style}]" if pri_style else t.priority.value

        title = t.title
        if t.status.value == "done":
            title = f"[strikethrough dim]{title}[/strikethrough dim]"
        elif t.description:
            title = f"{title}\n[dim]{t.description[:60]}[/dim]"

        due_str = ""
        if t.due_date:
            delta = (t.due_date - today).days
            if t.status.value == "done":
                due_str = f"[dim]{t.due_date}[/dim]"
            elif delta < 0:
                due_str = f"[bold red]{t.due_date} ({-delta}d late)[/bold red]"
            elif delta == 0:
                due_str = f"[bold yellow]Today[/bold yellow]"
            elif delta == 1:
                due_str = f"[yellow]Tomorrow[/yellow]"
            elif delta <= 7:
                due_str = f"{t.due_date.strftime('%A')}"
            else:
                due_str = str(t.due_date)

        table.add_row(str(t.id), icon, title, pri_label, due_str)

    console.print(table)
