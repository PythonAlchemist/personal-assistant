"""CLI entry point."""

import click

from assistant import config
from assistant.storage.database import get_connection, init_db
from assistant.cli.family import family
from assistant.cli.calendar import calendar
from assistant.cli.gmail import gmail
from assistant.cli.maps import maps
from assistant.cli.todo import todo
from assistant.cli.briefing import briefing
from assistant.cli.chat import chat


@click.group()
@click.pass_context
def cli(ctx):
    """Personal & family assistant."""
    ctx.ensure_object(dict)
    conn = get_connection(config.DB_PATH)
    init_db(conn)
    ctx.obj["db"] = conn


cli.add_command(family)
cli.add_command(calendar)
cli.add_command(gmail)
cli.add_command(maps)
cli.add_command(todo)
cli.add_command(briefing)
cli.add_command(chat)
