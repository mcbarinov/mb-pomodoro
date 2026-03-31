"""Permanently delete an interval."""

import time
from typing import Annotated

import typer
from mm_clikit import CliError

from mb_pomodoro.cli.context import use_context
from mb_pomodoro.time_utils import format_datetime, format_mmss


def delete(
    ctx: typer.Context,
    interval_id: Annotated[int | None, typer.Argument(help="Interval ID to delete. Defaults to latest.")] = None,
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Permanently delete an interval from history."""
    app = use_context(ctx)

    if not yes:
        # Pre-fetch for confirmation display
        if interval_id is not None:
            row = app.svc.fetch_interval(interval_id)
            if row is None:
                raise CliError(f"No interval with id {interval_id}.", "INTERVAL_NOT_FOUND")
        else:
            row = app.svc.fetch_latest_interval()
            if row is None:
                raise CliError("No intervals found.", "INTERVAL_NOT_FOUND")

        if app.out.json_mode:
            raise CliError("Use --yes flag to confirm deletion in JSON mode.", "CONFIRMATION_REQUIRED")

        now = int(time.time())
        worked = row.effective_worked(now)
        typer.echo(
            f"Interval {row.id}: {format_mmss(row.duration_sec)}, {row.status}, "
            f"worked {format_mmss(worked)}, started {format_datetime(row.started_at)}.",
        )
        answer = input("Type 'yes' to permanently delete this interval: ")
        if answer != "yes":
            raise CliError("Aborted: interval was not deleted.", "NOT_CONFIRMED")

    result = app.svc.delete_interval(interval_id)
    app.out.print_deleted(result)
