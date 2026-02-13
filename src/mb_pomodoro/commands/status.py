"""Show current Pomodoro timer status."""

import time

import typer

from mb_pomodoro import db
from mb_pomodoro.app_context import use_context
from mb_pomodoro.db import ACTIVE_STATUSES
from mb_pomodoro.output import StatusActiveResult, StatusInactiveResult


def status(ctx: typer.Context) -> None:
    """Show current Pomodoro timer status."""
    app_ctx = use_context(ctx)
    out, conn = app_ctx.out, app_ctx.conn

    row = db.fetch_latest_interval(conn)

    if row is None or row.status not in ACTIVE_STATUSES:
        out.print_status(StatusInactiveResult())
        return

    now = int(time.time())
    effective_worked = row.effective_worked(now)
    remaining = max(0, row.duration_sec - effective_worked)

    out.print_status(
        StatusActiveResult(
            interval_id=row.id,
            status=row.status,
            duration_sec=row.duration_sec,
            worked_sec=effective_worked,
            remaining_sec=remaining,
            started_at=row.started_at,
        )
    )
