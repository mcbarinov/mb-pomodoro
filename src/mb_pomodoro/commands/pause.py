"""Pause the active Pomodoro interval."""

import typer
from mm_clikit import use_context

from mb_pomodoro.service import Context


def pause(ctx: typer.Context) -> None:
    """Pause the active Pomodoro interval."""
    app = use_context(ctx, Context)
    result = app.svc.pause()
    app.out.print_paused(result)
