"""Start a new Pomodoro interval."""

import logging
import time
import uuid
from typing import Annotated

import typer

from mb_pomodoro import db
from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import ACTIVE_STATUSES
from mb_pomodoro.output import StartResult
from mb_pomodoro.time_fmt import parse_duration
from mb_pomodoro.timer_worker import spawn_timer_worker

logger = logging.getLogger(__name__)


def start(
    ctx: typer.Context,
    duration: Annotated[str | None, typer.Argument(help="Duration: 25 (minutes), 25m, 90s, 10m30s. Default from config.")] = None,
) -> None:
    """Start a new Pomodoro interval."""
    app_ctx = use_context(ctx)
    out, conn = app_ctx.out, app_ctx.conn

    if duration is None:
        duration = app_ctx.cfg.default_duration
    duration_sec = parse_duration(duration)
    if duration_sec is None or duration_sec <= 0:
        logger.warning("Invalid duration input: %s", duration)
        out.print_error_and_exit("INVALID_DURATION", f"Invalid duration: {duration}. Examples: 25, 25m, 90s, 10m30s.")

    # Check for an existing active interval
    latest = db.fetch_latest_interval(conn)
    if latest and latest.status in ACTIVE_STATUSES:
        out.print_interval_error_and_exit("ACTIVE_INTERVAL_EXISTS", "An active interval already exists.", latest)

    # Create new interval
    interval_id = str(uuid.uuid4())
    now = int(time.time())

    if not db.insert_interval(conn, interval_id, duration_sec, now):
        logger.warning("Start rejected: concurrent interval creation race")
        out.print_error_and_exit("ACTIVE_INTERVAL_EXISTS", "Another interval was started concurrently.")

    spawn_timer_worker(interval_id, app_ctx.cfg.data_dir)

    logger.info("Interval started id=%s duration=%ds", interval_id, duration_sec)
    out.print_started(StartResult(interval_id=interval_id, duration_sec=duration_sec, started_at=now))
