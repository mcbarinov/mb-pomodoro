"""Change the resolution of a completed or abandoned interval."""

from typing import Annotated

import typer
from mm_clikit import CliError

from mb_pomodoro.cli.context import use_context
from mb_pomodoro.time_utils import format_datetime, format_mmss

_RESOLUTION_HELP = "New resolution: 'completed' (honest work) or 'abandoned' (did not work)."


def re_resolve(
    ctx: typer.Context,
    interval_id: Annotated[int, typer.Argument(help="Interval ID to re-resolve.")],
    resolution: Annotated[str, typer.Argument(help=_RESOLUTION_HELP)],
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Change the resolution of a completed or abandoned interval."""
    app = use_context(ctx)

    if not yes:
        row = app.svc.fetch_interval(interval_id)
        if row is None:
            raise CliError(f"No interval with id {interval_id}.", "INTERVAL_NOT_FOUND")

        if app.out.json_mode:
            raise CliError("Use --yes flag to confirm in JSON mode.", "CONFIRMATION_REQUIRED")

        typer.echo(
            f"Interval {row.id}: currently {row.status}, "
            f"worked {format_mmss(row.worked_sec)}, started {format_datetime(row.started_at)}.",
        )
        typer.echo(f"Will change to: {resolution}.")
        answer = input("Type 'yes' to confirm: ")
        if answer != "yes":
            raise CliError("Aborted: interval was not changed.", "NOT_CONFIRMED")

    result = app.svc.re_resolve(interval_id, resolution)
    app.out.print_re_resolved(result)
