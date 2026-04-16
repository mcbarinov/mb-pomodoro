"""Resume a paused Pomodoro interval."""

import typer
from mm_clikit import spawn_daemon

from mb_pomodoro.cli.context import use_context


def resume(ctx: typer.Context) -> None:
    """Resume a paused Pomodoro interval."""
    app = use_context(ctx)
    result = app.core.service.resume()
    spawn_daemon([*app.core.config.base_argv(), "worker", str(result.interval_id)])
    app.out.print_resumed(result)
