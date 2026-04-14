"""Restart a running interval in place, keeping the same ID."""

import typer

from mb_pomodoro.cli.context import use_context


def restart(ctx: typer.Context) -> None:
    """Reset a running interval's counters. Same ID, fresh timer."""
    app = use_context(ctx)
    # The existing worker keeps polling and picks up the reset DB values on its
    # next tick -- no need to spawn or kill anything.
    result = app.core.service.restart()
    app.out.print_restarted(result)
