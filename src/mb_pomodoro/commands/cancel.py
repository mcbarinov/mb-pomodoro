"""Cancel the active Pomodoro interval."""

import typer
from mm_clikit import use_context

from mb_pomodoro.service import Context


def cancel(ctx: typer.Context) -> None:
    """Cancel the active Pomodoro interval."""
    app = use_context(ctx, Context)
    result = app.svc.cancel()
    app.out.print_cancelled(result)
