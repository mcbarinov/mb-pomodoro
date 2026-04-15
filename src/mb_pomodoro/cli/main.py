"""CLI app definition and initialization."""

import logging
import sys
from pathlib import Path
from types import TracebackType
from typing import Annotated

import typer
from mm_clikit import CoreContext, TyperPlus, setup_logging

from mb_pomodoro.cli.commands.cancel import cancel
from mb_pomodoro.cli.commands.edit.delete import delete
from mb_pomodoro.cli.commands.edit.re_resolve import re_resolve
from mb_pomodoro.cli.commands.edit.restart import restart
from mb_pomodoro.cli.commands.finish import finish
from mb_pomodoro.cli.commands.history import history
from mb_pomodoro.cli.commands.pause import pause
from mb_pomodoro.cli.commands.raycast.install import install as raycast_install
from mb_pomodoro.cli.commands.resume import resume
from mb_pomodoro.cli.commands.start import start
from mb_pomodoro.cli.commands.status import status
from mb_pomodoro.cli.commands.tray import tray
from mb_pomodoro.cli.commands.worker import worker
from mb_pomodoro.cli.output import Output
from mb_pomodoro.config import Config
from mb_pomodoro.core.core import Core


def _install_excepthook(logger: logging.Logger) -> None:
    """Route uncaught exceptions through the logging framework."""
    previous = sys.excepthook

    def _hook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, exc, tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        previous(exc_type, exc, tb)

    sys.excepthook = _hook


app = TyperPlus(package_name="mb-pomodoro")


@app.callback()
def main(
    ctx: typer.Context,
    *,
    data_dir: Annotated[
        Path | None,
        typer.Option("--data-dir", help="Data directory. Env: MB_POMODORO_DATA_DIR."),
    ] = None,
) -> None:
    """Pomodoro timer for macOS."""
    config = Config.build(data_dir)
    setup_logging("mb_pomodoro", file_path=config.log_path)
    _install_excepthook(logging.getLogger("mb_pomodoro"))
    core = Core(config)
    ctx.call_on_close(core.close)
    if ctx.invoked_subcommand not in {"worker", "tray"}:
        core.service.recover_stale()
    ctx.obj = CoreContext[Core, Output](core=core, out=Output())


app.command()(start)
app.command(aliases=["p"])(pause)
app.command(aliases=["r"])(resume)
app.command()(cancel)
app.command()(finish)
app.command(aliases=["h"])(history)
app.command(aliases=["s"])(status)
app.command()(tray)
app.command()(worker)

# Non-standard state edits: off-plan operations grouped under `edit`.
edit_app = TyperPlus()
edit_app.command(name="delete")(delete)
edit_app.command(name="re-resolve")(re_resolve)
edit_app.command(name="restart")(restart)
app.add_typer(edit_app, name="edit", help="Off-plan state edits: delete, re-resolve, restart.")

raycast_app = TyperPlus()
raycast_app.command(name="install")(raycast_install)
app.add_typer(raycast_app, name="raycast", help="Manage Raycast script commands.")
