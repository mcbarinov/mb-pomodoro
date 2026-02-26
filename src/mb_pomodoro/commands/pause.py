"""Pause the active Pomodoro interval."""

import logging
import time

import typer

from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import IntervalStatus
from mb_pomodoro.output import PauseResult

logger = logging.getLogger(__name__)


def pause(ctx: typer.Context) -> None:
    """Pause the active Pomodoro interval."""
    app = use_context(ctx)

    row = app.db.fetch_latest_interval()
    if row is None or row.status != IntervalStatus.RUNNING or row.run_started_at is None:
        msg = "No running interval to pause."
        if row is not None:
            msg = f"{msg} Latest interval: id={row.id}, status={row.status}."
        app.out.print_error_and_exit("NOT_RUNNING", msg)

    now = int(time.time())
    new_worked = row.effective_worked(now)

    if not app.db.pause_interval(row.id, new_worked, now):
        logger.warning("Pause rejected: concurrent modification id=%s", row.id)
        app.out.print_error_and_exit("CONCURRENT_MODIFICATION", "Interval was modified concurrently.")

    remaining = row.duration_sec - new_worked
    logger.info("Interval paused id=%s worked=%ds remaining=%ds", row.id, new_worked, remaining)
    app.out.print_paused(PauseResult(interval_id=row.id, worked_sec=new_worked, remaining_sec=remaining))
