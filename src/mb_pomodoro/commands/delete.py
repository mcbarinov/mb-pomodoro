"""Permanently delete an interval."""

import time
from typing import Annotated

import typer
from mm_clikit import use_context

from mb_pomodoro.errors import AppError
from mb_pomodoro.service import Context
from mb_pomodoro.time_utils import format_datetime, format_mmss


def delete(
    ctx: typer.Context,
    interval_id: Annotated[int | None, typer.Argument(help="Interval ID to delete. Defaults to latest.")] = None,
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Permanently delete an interval from history."""
    app = use_context(ctx, Context)

    if not yes:
        # Pre-fetch for confirmation display
        if interval_id is not None:
            row = app.svc.fetch_interval(interval_id)
            if row is None:
                raise AppError("INTERVAL_NOT_FOUND", f"No interval with id {interval_id}.")
        else:
            row = app.svc.fetch_latest_interval()
            if row is None:
                raise AppError("INTERVAL_NOT_FOUND", "No intervals found.")

        if app.out.json_mode:
            raise AppError("CONFIRMATION_REQUIRED", "Use --yes flag to confirm deletion in JSON mode.")

        now = int(time.time())
        worked = row.effective_worked(now)
        typer.echo(
            f"Interval {row.id}: {format_mmss(row.duration_sec)}, {row.status}, "
            f"worked {format_mmss(worked)}, started {format_datetime(row.started_at)}.",
        )
        answer = input("Type 'yes' to permanently delete this interval: ")
        if answer != "yes":
            raise AppError("NOT_CONFIRMED", "Aborted: interval was not deleted.")

    result = app.svc.delete_interval(interval_id)
    app.out.print_deleted(result)
