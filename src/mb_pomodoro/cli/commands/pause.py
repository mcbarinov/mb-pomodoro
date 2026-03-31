"""Pause the active Pomodoro interval."""

import typer

from mb_pomodoro.cli.context import use_context


def pause(ctx: typer.Context) -> None:
    """Pause the active Pomodoro interval."""
    app = use_context(ctx)
    result = app.svc.pause()
    app.out.print_paused(result)
