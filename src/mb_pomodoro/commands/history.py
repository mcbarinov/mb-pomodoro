"""Show Pomodoro session history."""

import time
from typing import Annotated

import typer

from mb_pomodoro import db
from mb_pomodoro.app_context import use_context
from mb_pomodoro.output import HistoryItem, HistoryResult


def history(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum number of entries to show.")] = 10,
) -> None:
    """Show Pomodoro session history."""
    app = use_context(ctx)

    rows = db.fetch_history(app.conn, limit)

    now = int(time.time())
    items: list[HistoryItem] = []
    for row in rows:
        effective_worked = row.effective_worked(now)
        items.append(
            HistoryItem(
                interval_id=row.id,
                status=row.status,
                duration_sec=row.duration_sec,
                worked_sec=effective_worked,
                started_at=row.started_at,
            )
        )

    app.out.print_history(HistoryResult(intervals=items))
