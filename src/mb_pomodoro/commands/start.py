"""Start a new Pomodoro interval."""

from typing import Annotated

import typer
from mm_clikit import spawn_daemon

from mb_pomodoro.app_context import use_context
from mb_pomodoro.pomodoro import PomodoroError


def start(
    ctx: typer.Context,
    duration: Annotated[str | None, typer.Argument(help="Duration: 25 (minutes), 25m, 90s, 10m30s. Default from config.")] = None,
) -> None:
    """Start a new Pomodoro interval."""
    app = use_context(ctx)

    try:
        result = app.pomodoro.start(duration)
    except PomodoroError as e:
        app.out.print_error_and_exit(e.code, str(e))

    spawn_daemon([*app.cfg.cli_base_args(), "worker", str(result.interval_id)])
    app.out.print_started(result)
