"""Cancel the active Pomodoro interval."""

import logging
import time

import typer

from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import IntervalStatus
from mb_pomodoro.output import CancelResult

logger = logging.getLogger(__name__)


def cancel(ctx: typer.Context) -> None:
    """Cancel the active Pomodoro interval."""
    app = use_context(ctx)

    row = app.db.fetch_latest_interval()
    if row is None or row.status not in (IntervalStatus.RUNNING, IntervalStatus.PAUSED, IntervalStatus.INTERRUPTED):
        msg = "No active interval to cancel."
        if row is not None:
            msg = f"{msg} Latest interval: id={row.id}, status={row.status}."
        app.out.print_error_and_exit("NO_ACTIVE_INTERVAL", msg)

    now = int(time.time())
    new_worked = row.effective_worked(now)

    if not app.db.cancel_interval(row.id, new_worked, now):
        logger.warning("Cancel rejected: concurrent modification id=%s", row.id)
        app.out.print_error_and_exit("CONCURRENT_MODIFICATION", "Interval was modified concurrently.")

    logger.info("Interval cancelled id=%s worked=%ds", row.id, new_worked)
    app.out.print_cancelled(CancelResult(interval_id=row.id, worked_sec=new_worked))
