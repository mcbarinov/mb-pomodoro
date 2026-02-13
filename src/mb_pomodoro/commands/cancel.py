"""Cancel the active Pomodoro interval."""

import logging
import time

import typer

from mb_pomodoro import db
from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import IntervalStatus
from mb_pomodoro.output import CancelResult

logger = logging.getLogger(__name__)


def cancel(ctx: typer.Context) -> None:
    """Cancel the active Pomodoro interval."""
    app_ctx = use_context(ctx)
    out, conn = app_ctx.out, app_ctx.conn

    row = db.fetch_latest_interval(conn)
    if row is None or row.status not in (IntervalStatus.RUNNING, IntervalStatus.PAUSED, IntervalStatus.INTERRUPTED):
        out.print_interval_error_and_exit("NO_ACTIVE_INTERVAL", "No active interval to cancel.", row)

    now = int(time.time())
    new_worked = row.effective_worked(now)

    if not db.cancel_interval(conn, row.id, new_worked, now):
        logger.warning("Cancel rejected: concurrent modification id=%s", row.id)
        out.print_error_and_exit("CONCURRENT_MODIFICATION", "Interval was modified concurrently.")

    logger.info("Interval cancelled id=%s worked=%ds", row.id, new_worked)
    out.print_cancelled(CancelResult(interval_id=row.id, worked_sec=new_worked))
