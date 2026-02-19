"""Application context shared across CLI commands."""

from dataclasses import dataclass

import typer

from mb_pomodoro.config import Config
from mb_pomodoro.db import Db
from mb_pomodoro.output import Output


@dataclass(frozen=True, slots=True)
class AppContext:
    """Shared application state passed through Typer context."""

    out: Output
    db: Db
    cfg: Config


def use_context(ctx: typer.Context) -> AppContext:
    """Extract application context from Typer context."""
    result: AppContext = ctx.obj
    return result
