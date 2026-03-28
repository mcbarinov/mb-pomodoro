"""Pause the active Pomodoro interval."""

import typer

from mb_pomodoro.app_context import use_context
from mb_pomodoro.pomodoro import PomodoroError


def pause(ctx: typer.Context) -> None:
    """Pause the active Pomodoro interval."""
    app = use_context(ctx)

    try:
        result = app.pomodoro.pause()
    except PomodoroError as e:
        app.out.print_error_and_exit(e.code, str(e))

    app.out.print_paused(result)
