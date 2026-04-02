"""Menu bar tray CLI command."""

import time
from typing import Annotated

import typer
from mm_clikit import CliError, is_process_running, read_pid_file, spawn_daemon, stop_process

from mb_pomodoro.cli.context import use_context
from mb_pomodoro.core.results import TrayStartResult, TrayStopResult
from mb_pomodoro.tray import run_foreground

_STOP_TIMEOUT_SEC = 2.0
_LAUNCH_VERIFY_SEC = 0.5


def _stop_tray(ctx: typer.Context) -> None:
    """Stop a running tray process via SIGTERM with SIGKILL fallback."""
    app = use_context(ctx)

    pid = read_pid_file(app.core.config.tray_pid_path)
    if pid is None or not is_process_running(app.core.config.tray_pid_path, command_contains="mb-pomodoro"):
        app.core.config.tray_pid_path.unlink(missing_ok=True)
        raise CliError("Tray is not running.", "TRAY_NOT_RUNNING")

    stop_process(pid, timeout=_STOP_TIMEOUT_SEC)
    app.core.config.tray_pid_path.unlink(missing_ok=True)
    app.out.print_tray_stopped(TrayStopResult(pid=pid))


def _run_tray_foreground(ctx: typer.Context) -> None:
    """Run the tray in foreground (blocking). Used by the background spawner."""
    app = use_context(ctx)

    if is_process_running(app.core.config.tray_pid_path, command_contains="mb-pomodoro"):
        raise CliError("Tray is already running.", "TRAY_ALREADY_RUNNING")

    run_foreground(app.core.config)


def _launch_background(ctx: typer.Context) -> None:
    """Spawn tray in background, verify it started, print PID."""
    app = use_context(ctx)

    if is_process_running(app.core.config.tray_pid_path, command_contains="mb-pomodoro"):
        pid = read_pid_file(app.core.config.tray_pid_path)
        raise CliError(f"Tray is already running (pid {pid}).", "TRAY_ALREADY_RUNNING")

    pid = spawn_daemon([*app.core.config.cli_base_args(), "tray", "--run"])

    # Brief wait to verify the process is alive
    time.sleep(_LAUNCH_VERIFY_SEC)
    if not is_process_running(app.core.config.tray_pid_path, command_contains="mb-pomodoro"):
        raise CliError("Tray process failed to start.", "TRAY_LAUNCH_FAILED")

    app.out.print_tray_started(TrayStartResult(pid=pid))


def tray(
    ctx: typer.Context,
    *,
    stop: Annotated[bool, typer.Option("--stop", help="Stop the running tray process.")] = False,
    run: Annotated[bool, typer.Option("--run", hidden=True, help="Run tray in foreground (internal).")] = False,
) -> None:
    """Run menu bar status icon that displays current timer state."""
    if stop:
        _stop_tray(ctx)
    elif run:
        _run_tray_foreground(ctx)
    else:
        _launch_background(ctx)
