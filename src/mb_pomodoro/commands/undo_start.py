"""Permanently delete an accidentally started interval."""

import logging
import time
from typing import Annotated

import typer

from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import IntervalStatus
from mb_pomodoro.output import UndoStartResult
from mb_pomodoro.time_utils import format_mmss

logger = logging.getLogger(__name__)


def undo_start(
    ctx: typer.Context,
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Permanently delete the active interval, as if it never existed."""
    app = use_context(ctx)

    row = app.db.fetch_latest_interval()
    if row is None or row.status != IntervalStatus.RUNNING:
        msg = "No running interval to undo."
        if row is not None:
            msg = f"{msg} Latest interval: id={row.id}, status={row.status}."
        app.out.print_error_and_exit("NOT_RUNNING", msg)

    now = int(time.time())
    elapsed = now - row.started_at
    worked = row.effective_worked(now)

    if not yes:
        if app.out.json_mode:
            app.out.print_error_and_exit("CONFIRMATION_REQUIRED", "Use --yes flag to confirm deletion in JSON mode.")
        duration = format_mmss(row.duration_sec)
        typer.echo(
            f"Active interval: {duration}, {row.status}, worked {format_mmss(worked)} ({format_mmss(elapsed)} since start)."
        )
        answer = input("Type 'yes' to permanently delete this interval: ")
        if answer != "yes":
            app.out.print_error_and_exit("NOT_CONFIRMED", "Aborted: interval was not deleted.")

    app.db.delete_interval(row.id)
    logger.info("Interval deleted (undo-start) id=%s status=%s worked=%ds", row.id, row.status, worked)
    app.out.print_undo_start(UndoStartResult(interval_id=row.id))
