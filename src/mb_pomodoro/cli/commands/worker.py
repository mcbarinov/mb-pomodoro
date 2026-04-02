"""Background timer worker CLI command."""

from typing import Annotated

import typer

from mb_pomodoro.cli.context import use_context
from mb_pomodoro.worker import run_worker


def worker(
    ctx: typer.Context,
    interval_id: Annotated[int, typer.Argument(help="Interval ID to track.")],
) -> None:
    """Run background timer worker. Not intended for manual use."""
    app = use_context(ctx)
    run_worker(app.core, interval_id)
