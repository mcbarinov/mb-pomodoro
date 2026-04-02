"""Show current Pomodoro timer status."""

from typing import Annotated

import typer

from mb_pomodoro.cli.context import use_context


def status(
    ctx: typer.Context,
    *,
    short: Annotated[bool, typer.Option("--short", help="Single-line output.")] = False,
) -> None:
    """Show current Pomodoro timer status."""
    app = use_context(ctx)
    result = app.core.service.status()
    app.out.print_status(result, short=short)
