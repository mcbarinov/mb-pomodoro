"""Resume a paused Pomodoro interval."""

import typer
from mm_clikit import spawn_daemon, use_context

from mb_pomodoro.service import Context


def resume(ctx: typer.Context) -> None:
    """Resume a paused Pomodoro interval."""
    app = use_context(ctx, Context)
    result = app.svc.resume()
    spawn_daemon([*app.cfg.cli_base_args(), "worker", str(result.interval_id)])
    app.out.print_resumed(result)
