"""Resolve a finished Pomodoro interval as completed or abandoned.

Fallback for when the completion dialog was missed or failed.
"""

import logging
import time
from typing import Annotated

import typer

from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import IntervalStatus
from mb_pomodoro.output import FinishResult

logger = logging.getLogger(__name__)

_RESOLUTION_HELP = "Resolution: 'completed' (honest work) or 'abandoned' (did not work)."


def finish(ctx: typer.Context, resolution: Annotated[str, typer.Argument(help=_RESOLUTION_HELP)]) -> None:
    """Resolve a finished interval. Fallback for when the completion dialog was missed or failed."""
    app = use_context(ctx)

    if resolution not in (IntervalStatus.COMPLETED, IntervalStatus.ABANDONED):
        app.out.print_error_and_exit("INVALID_RESOLUTION", "Resolution must be 'completed' or 'abandoned'.")

    resolved_status = IntervalStatus(resolution)

    row = app.db.fetch_latest_interval()
    if row is None or row.status != IntervalStatus.FINISHED:
        msg = "No finished interval to resolve."
        if row is not None:
            msg = f"{msg} Latest interval: id={row.id}, status={row.status}."
        app.out.print_error_and_exit("NOT_FINISHED", msg)

    now = int(time.time())
    if not app.db.resolve_interval(row.id, resolved_status, now):
        logger.warning("Finish rejected: concurrent modification id=%s", row.id)
        app.out.print_error_and_exit("CONCURRENT_MODIFICATION", "Interval was modified concurrently.")

    logger.info("Interval resolved id=%s resolution=%s", row.id, resolved_status)
    app.out.print_finished(FinishResult(interval_id=row.id, resolution=resolved_status, worked_sec=row.worked_sec))
