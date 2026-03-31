"""Show current Pomodoro timer status."""

from typing import Annotated

import typer
from mm_clikit import use_context

from mb_pomodoro.service import Context


def status(
    ctx: typer.Context,
    *,
    short: Annotated[bool, typer.Option("--short", help="Single-line output.")] = False,
) -> None:
    """Show current Pomodoro timer status."""
    app = use_context(ctx, Context)
    result = app.svc.status()
    app.out.print_status(result, short=short)
