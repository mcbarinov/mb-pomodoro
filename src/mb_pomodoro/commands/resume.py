"""Resume a paused Pomodoro interval."""

import typer
from mm_clikit import spawn_daemon

from mb_pomodoro.app_context import use_context
from mb_pomodoro.pomodoro import PomodoroError


def resume(ctx: typer.Context) -> None:
    """Resume a paused Pomodoro interval."""
    app = use_context(ctx)

    try:
        result = app.pomodoro.resume()
    except PomodoroError as e:
        app.out.print_error_and_exit(e.code, str(e))

    spawn_daemon([*app.cfg.cli_base_args(), "worker", str(result.interval_id)])
    app.out.print_resumed(result)
