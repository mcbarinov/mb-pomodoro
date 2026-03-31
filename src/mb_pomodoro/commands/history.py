"""Show Pomodoro session history."""

from typing import Annotated

import typer
from mm_clikit import use_context

from mb_pomodoro.service import Context


def history(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum number of entries to show.")] = 10,
    daily: Annotated[bool, typer.Option("--daily", "-d", help="Show completed count per day.")] = False,
) -> None:
    """Show Pomodoro session history."""
    app = use_context(ctx, Context)

    if daily:
        daily_result = app.svc.daily_history(limit)
        app.out.print_daily_history(daily_result)
        return

    history_result = app.svc.history(limit)
    app.out.print_history(history_result)
