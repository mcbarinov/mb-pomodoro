"""CLI entry point for mb-pomodoro."""

from pathlib import Path
from typing import Annotated

import typer
from mm_clikit import AppContext, TyperPlus, get_json_mode, setup_logging

from mb_pomodoro.commands.cancel import cancel
from mb_pomodoro.commands.delete import delete
from mb_pomodoro.commands.finish import finish
from mb_pomodoro.commands.history import history
from mb_pomodoro.commands.pause import pause
from mb_pomodoro.commands.re_resolve import re_resolve
from mb_pomodoro.commands.resume import resume
from mb_pomodoro.commands.start import start
from mb_pomodoro.commands.status import status
from mb_pomodoro.commands.tray import tray
from mb_pomodoro.commands.worker import worker
from mb_pomodoro.config import Config
from mb_pomodoro.db import Db
from mb_pomodoro.output import Output
from mb_pomodoro.service import Service

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
    cfg = Config.build(data_dir)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    setup_logging("mb_pomodoro", cfg.log_path)
    db = Db(cfg.db_path)
    ctx.call_on_close(db.close)
    svc = Service(db, cfg)
    if ctx.invoked_subcommand not in {"worker", "tray"}:
        svc.recover_stale()
    ctx.obj = AppContext(svc=svc, out=Output(json_mode=get_json_mode()), cfg=cfg)


app.command()(start)
app.command(aliases=["p"])(pause)
app.command(aliases=["r"])(resume)
app.command()(cancel)
app.command()(finish)
app.command()(delete)
app.command(name="re-resolve")(re_resolve)
app.command(aliases=["h"])(history)
app.command(aliases=["s"])(status)
app.command()(tray)
app.command()(worker)
