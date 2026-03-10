"""Gmail CLI commands."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from assistant import config
from assistant.services import gmail as gmail_svc

console = Console()

ACCOUNT_NAMES = list(config.GOOGLE_ACCOUNTS.keys())


def _handle_gmail_error(fn):
    """Decorator to catch common Gmail errors."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
        except Exception as e:
            console.print(f"[red]Gmail error: {e}[/red]")
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


@click.group()
def gmail():
    """Gmail integration."""
    pass


@gmail.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default=None,
              help="Account (omit to show all)")
@_handle_gmail_error
def status(account: str | None):
    """Show inbox status for accounts."""
    accounts = [account] if account else _authenticated_accounts()
    table = Table(title="Gmail Status")
    table.add_column("Account", style="bold")
    table.add_column("Email")
    table.add_column("Unread", justify="right")
    for acct in accounts:
        profile = gmail_svc.get_profile(acct)
        unread = gmail_svc.get_unread_count(acct)
        unread_style = "bold red" if unread > 0 else "green"
        table.add_row(acct, profile["email"], f"[{unread_style}]{unread}[/{unread_style}]")
    console.print(table)


@gmail.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default=None,
              help="Account (omit to show all)")
@click.option("--max", "-n", "max_results", default=15, help="Number of messages to show")
@click.option("--unread", is_flag=True, help="Show only unread messages")
@_handle_gmail_error
def inbox(account: str | None, max_results: int, unread: bool):
    """Show recent inbox messages."""
    accounts = [account] if account else _authenticated_accounts()
    query = "in:inbox"
    if unread:
        query += " is:unread"

    all_messages = []
    for acct in accounts:
        messages = gmail_svc.list_messages(acct, query=query, max_results=max_results)
        for m in messages:
            m["_account"] = acct
        all_messages.extend(messages)

    if not all_messages:
        console.print("[dim]No messages found.[/dim]")
        return

    _print_message_list(all_messages, show_account=len(accounts) > 1)


@gmail.command()
@click.argument("query")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default=None,
              help="Account (omit to search all)")
@click.option("--max", "-n", "max_results", default=15)
@_handle_gmail_error
def search(query: str, account: str | None, max_results: int):
    """Search messages using Gmail query syntax."""
    accounts = [account] if account else _authenticated_accounts()
    all_messages = []
    for acct in accounts:
        messages = gmail_svc.search(query, acct, max_results)
        for m in messages:
            m["_account"] = acct
        all_messages.extend(messages)

    if not all_messages:
        console.print("[dim]No messages found.[/dim]")
        return

    _print_message_list(all_messages, show_account=len(accounts) > 1)


@gmail.command()
@click.argument("message_id")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@_handle_gmail_error
def read(message_id: str, account: str):
    """Read a specific message by ID."""
    msg = gmail_svc.read_message(message_id, account)
    gmail_svc.mark_read(message_id, account)

    header = f"[bold]{msg['subject']}[/bold]\n"
    header += f"From: {msg['from']}\n"
    header += f"To: {msg['to']}\n"
    header += f"Date: {msg['date']}"

    console.print(Panel(header, title="Message", border_style="blue"))
    console.print()
    console.print(msg["body"])


@gmail.command()
@click.option("--to", "-t", required=True, help="Recipient email")
@click.option("--subject", "-s", required=True, help="Subject line")
@click.option("--body", "-b", required=True, help="Message body")
@click.option("--cc", default="")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@click.confirmation_option(prompt="Send this email?")
@_handle_gmail_error
def send(to: str, subject: str, body: str, cc: str, account: str):
    """Send an email."""
    result = gmail_svc.send_message(to=to, subject=subject, body=body, account=account, cc=cc)
    console.print(f"[green]Sent! Message ID: {result['id']}[/green]")


@gmail.command()
@click.argument("message_id")
@click.option("--body", "-b", required=True, help="Reply body")
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@click.confirmation_option(prompt="Send this reply?")
@_handle_gmail_error
def reply(message_id: str, body: str, account: str):
    """Reply to a message."""
    result = gmail_svc.reply_to_message(message_id, body, account)
    console.print(f"[green]Reply sent! Message ID: {result['id']}[/green]")


@gmail.command()
@click.option("--account", "-a", type=click.Choice(ACCOUNT_NAMES), default="personal")
@_handle_gmail_error
def labels(account: str):
    """List Gmail labels."""
    label_list = gmail_svc.list_labels(account)
    table = Table(title=f"Labels — {account}")
    table.add_column("Name", style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Type")
    for l in sorted(label_list, key=lambda x: x["name"]):
        table.add_row(l["name"], l["id"], l["type"])
    console.print(table)


def _authenticated_accounts() -> list[str]:
    return [alias for alias in ACCOUNT_NAMES if config.google_token_path(alias).exists()]


def _print_message_list(messages: list[dict], show_account: bool = False):
    """Pretty-print a list of messages."""
    table = Table()
    table.add_column("", width=2)  # unread indicator
    if show_account:
        table.add_column("Account", style="cyan", width=10)
    table.add_column("From", width=25, no_wrap=True)
    table.add_column("Subject", min_width=30)
    table.add_column("Date", style="dim", width=18, no_wrap=True)
    table.add_column("ID", style="dim", width=16)

    for m in messages:
        unread = "[bold yellow]*[/bold yellow]" if m.get("unread") else " "
        subject = m["subject"]
        if m.get("unread"):
            subject = f"[bold]{subject}[/bold]"

        row = [unread]
        if show_account:
            row.append(m.get("_account", ""))
        # Truncate from field for display
        from_field = m["from"]
        if len(from_field) > 25:
            from_field = from_field[:24] + "…"
        row.extend([from_field, subject, m["date"][:18], m["id"][:16]])
        table.add_row(*row)

    console.print(table)
