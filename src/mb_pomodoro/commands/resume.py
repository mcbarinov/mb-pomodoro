"""Resume a paused Pomodoro interval."""

import logging
import time

import typer

from mb_pomodoro import db
from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import IntervalStatus
from mb_pomodoro.output import ResumeResult
from mb_pomodoro.timer_worker import spawn_timer_worker

logger = logging.getLogger(__name__)


def resume(ctx: typer.Context) -> None:
    """Resume a paused Pomodoro interval."""
    app_ctx = use_context(ctx)
    out, conn = app_ctx.out, app_ctx.conn

    row = db.fetch_latest_interval(conn)
    if row is None or row.status not in (IntervalStatus.PAUSED, IntervalStatus.INTERRUPTED):
        out.print_interval_error_and_exit("NOT_RESUMABLE", "No paused or interrupted interval to resume.", row)

    now = int(time.time())

    if not db.resume_interval(conn, row.id, now):
        logger.warning("Resume rejected: concurrent modification id=%s", row.id)
        out.print_error_and_exit("CONCURRENT_MODIFICATION", "Interval was modified concurrently.")

    spawn_timer_worker(row.id, app_ctx.cfg.data_dir)

    remaining = row.duration_sec - row.worked_sec
    logger.info("Interval resumed id=%s worked=%ds remaining=%ds", row.id, row.worked_sec, remaining)
    out.print_resumed(ResumeResult(interval_id=row.id, worked_sec=row.worked_sec, remaining_sec=remaining))
