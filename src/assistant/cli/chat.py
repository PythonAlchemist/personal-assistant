"""Interactive chat mode."""

import click
from rich.console import Console
from rich.markdown import Markdown

from assistant.services.family import summarize_family

console = Console()

SYSTEM_PROMPT = """You are a helpful family assistant. You know the following about this family:

{family_context}

Help with scheduling, planning, reminders, and general family organization.
Today's date is {today}.
Be concise and practical in your responses."""


@click.command()
def chat():
    """Start an interactive chat session."""
    try:
        import anthropic
    except ImportError:
        console.print("[red]Chat requires the anthropic package.[/red]")
        console.print("Install with: uv pip install -e '.[chat]'")
        return

    from assistant import config
    if not config.ANTHROPIC_API_KEY:
        console.print("[red]Set ANTHROPIC_API_KEY environment variable to use chat.[/red]")
        return

    from datetime import date

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    family_context = summarize_family()
    system = SYSTEM_PROMPT.format(family_context=family_context, today=date.today())

    messages = []
    console.print("[bold]Family Assistant Chat[/bold] (type 'quit' to exit)\n")

    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            console.print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system,
                messages=messages,
            )
            reply = response.content[0].text
            messages.append({"role": "assistant", "content": reply})
            console.print()
            console.print(Markdown(reply))
            console.print()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
