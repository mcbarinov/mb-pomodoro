"""Menu bar status icon for the Pomodoro timer."""

# pyright: reportAttributeAccessIssue=false
# PyObjC generates AppKit/Foundation bindings at runtime, invisible to static analysis

import contextlib
import os
import signal
import subprocess
import threading
import time
from typing import Annotated, Any, Self

import objc
import typer
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSMenu, NSMenuItem, NSStatusBar
from Foundation import NSDate, NSDefaultRunLoopMode, NSObject, NSRunLoop, NSTimer
from PyObjCTools import AppHelper

from mb_pomodoro.app_context import use_context
from mb_pomodoro.config import Config
from mb_pomodoro.db import ACTIVE_STATUSES, Db, IntervalRow, IntervalStatus
from mb_pomodoro.output import TrayStartResult, TrayStopResult
from mb_pomodoro.process import is_alive, read_pid, spawn_tray, write_pid_file
from mb_pomodoro.time_utils import format_mmss, parse_duration

_POLL_INTERVAL_SEC = 2.0
_STOP_TIMEOUT_SEC = 2.0
_LAUNCH_VERIFY_SEC = 0.5

# Action items visibility per status: (start_hidden, pause_hidden, resume_hidden)
_ACTION_VISIBILITY: dict[IntervalStatus | None, tuple[bool, bool, bool]] = {
    None: (False, True, True),
    IntervalStatus.RUNNING: (True, False, True),
    IntervalStatus.PAUSED: (True, True, False),
    IntervalStatus.INTERRUPTED: (True, True, False),
    IntervalStatus.FINISHED: (True, True, True),
}


def _format_title(row: IntervalRow | None, today_completed: int) -> str:
    """Build the menu bar title string from the latest interval and today's count."""
    if row is None or row.status not in ACTIVE_STATUSES:
        icon = "\u25c7"
    elif row.status == IntervalStatus.FINISHED:
        icon = "\u2713"
    elif row.status in {IntervalStatus.PAUSED, IntervalStatus.INTERRUPTED}:
        icon = "\u23f8"
    else:
        icon = "\u25b6"
    if today_completed > 0:
        return f"{icon} {today_completed}"
    return icon


class _TrayDelegate(NSObject):  # type: ignore[misc]
    """NSObject delegate that handles timer callbacks and menu actions."""

    db: Db
    cfg: Config
    status_item: Any
    # Menu items — info
    status_menu_item: Any
    duration_item: Any
    worked_item: Any
    left_item: Any
    today_completed_item: Any
    # Menu items — actions
    start_item: Any
    pause_item: Any
    resume_item: Any

    def initWithDb_cfg_statusItem_(self, db: Db, cfg: Config, status_item: object) -> Self:  # noqa: N802
        """Initialize delegate with DB handle, config, and status bar item."""
        self = objc.super(_TrayDelegate, self).init()  # noqa: PLW0642
        self.db = db
        self.cfg = cfg
        self.status_item = status_item
        return self

    def buildMenu(self) -> None:  # noqa: N802
        """Create the menu, all menu items, and attach to the status bar item."""
        menu = NSMenu.alloc().init()

        # Action items (only one visible at a time)
        self.start_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Start", "startPomodoro:", "")
        self.start_item.setTarget_(self)
        menu.addItem_(self.start_item)

        self.pause_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Pause", "pausePomodoro:", "")
        self.pause_item.setTarget_(self)
        self.pause_item.setHidden_(True)
        menu.addItem_(self.pause_item)

        self.resume_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Resume", "resumePomodoro:", "")
        self.resume_item.setTarget_(self)
        self.resume_item.setHidden_(True)
        menu.addItem_(self.resume_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Info items
        self.status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("No active interval", None, "")
        self.status_menu_item.setEnabled_(False)
        menu.addItem_(self.status_menu_item)

        self.duration_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Duration: --:--", None, "")
        self.duration_item.setEnabled_(False)
        self.duration_item.setHidden_(True)
        menu.addItem_(self.duration_item)

        self.worked_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Worked: --:--", None, "")
        self.worked_item.setEnabled_(False)
        self.worked_item.setHidden_(True)
        menu.addItem_(self.worked_item)

        self.left_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Left: --:--", None, "")
        self.left_item.setEnabled_(False)
        self.left_item.setHidden_(True)
        menu.addItem_(self.left_item)

        self.today_completed_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Today: 0 completed", None, "")
        self.today_completed_item.setEnabled_(False)
        self.today_completed_item.setHidden_(True)
        menu.addItem_(self.today_completed_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "quit:", "")
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def refresh_(self, _timer: object) -> None:
        """Timer callback: poll DB and update menu bar title and detail items."""
        row = self.db.fetch_latest_interval()
        now = int(time.time())
        today_completed = self.db.count_today_completed(now)

        self.status_item.setTitle_(_format_title(row, today_completed))

        # Today's completed count
        if today_completed > 0:
            self.today_completed_item.setTitle_(f"Today: {today_completed} completed")
            self.today_completed_item.setHidden_(False)
        else:
            self.today_completed_item.setHidden_(True)

        # Action items visibility
        status_key = row.status if row is not None and row.status in ACTIVE_STATUSES else None
        if status_key is None:
            duration_sec = parse_duration(self.cfg.default_duration) or 0
            self.start_item.setTitle_(f"Start ({format_mmss(duration_sec)})")
        start_hidden, pause_hidden, resume_hidden = _ACTION_VISIBILITY[status_key]
        self.start_item.setHidden_(start_hidden)
        self.pause_item.setHidden_(pause_hidden)
        self.resume_item.setHidden_(resume_hidden)

        # Info items
        if row is not None and row.status in ACTIVE_STATUSES:
            effective = row.effective_worked(now)
            remaining = max(0, row.duration_sec - effective)
            self.status_menu_item.setTitle_(f"Status: {row.status}")
            self.duration_item.setTitle_(f"Duration: {format_mmss(row.duration_sec)}")
            self.duration_item.setHidden_(False)
            self.worked_item.setTitle_(f"Worked: {format_mmss(effective)}")
            self.worked_item.setHidden_(False)
            self.left_item.setTitle_(f"Left: {format_mmss(remaining)}")
            self.left_item.setHidden_(False)
        else:
            self.status_menu_item.setTitle_("No active interval")
            self.duration_item.setHidden_(True)
            self.worked_item.setHidden_(True)
            self.left_item.setHidden_(True)

    def startPomodoro_(self, _sender: object) -> None:  # noqa: N802
        """Start a new pomodoro interval."""
        _run_cli(self, "start")

    def pausePomodoro_(self, _sender: object) -> None:  # noqa: N802
        """Pause the running interval."""
        _run_cli(self, "pause")

    def resumePomodoro_(self, _sender: object) -> None:  # noqa: N802
        """Resume a paused or interrupted interval."""
        _run_cli(self, "resume")

    def quit_(self, _sender: object) -> None:
        """Quit menu item callback."""
        NSApplication.sharedApplication().terminate_(None)


def _run_cli(delegate: _TrayDelegate, command: str) -> None:
    """Run a CLI command in a background thread, then refresh the menu."""
    data_dir = str(delegate.cfg.data_dir)

    def _task() -> None:
        # S603/S607: args are controlled literals, "mb-pomodoro" is our own CLI entry point
        subprocess.run(  # noqa: S603
            ["mb-pomodoro", "--data-dir", data_dir, "--json", command],  # noqa: S607
            capture_output=True,
            check=False,
        )
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_("refresh:", None, False)

    threading.Thread(target=_task, daemon=True).start()


def _run_tray(db: Db, cfg: Config) -> None:
    """Set up NSStatusBar item and run the event loop."""
    nsapp = NSApplication.sharedApplication()
    nsapp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
    status_item.setTitle_("\u25c7")

    delegate = _TrayDelegate.alloc().initWithDb_cfg_statusItem_(db, cfg, status_item)
    delegate.buildMenu()

    # Polling timer
    timer = NSTimer.alloc().initWithFireDate_interval_target_selector_userInfo_repeats_(
        NSDate.date(), _POLL_INTERVAL_SEC, delegate, "refresh:", None, True
    )
    NSRunLoop.currentRunLoop().addTimer_forMode_(timer, NSDefaultRunLoopMode)

    nsapp.setDelegate_(delegate)
    AppHelper.installMachInterrupt()
    AppHelper.runEventLoop()


def _stop_tray(ctx: typer.Context) -> None:
    """Stop a running tray process via SIGTERM with SIGKILL fallback."""
    app = use_context(ctx)
    pid_path = app.cfg.tray_pid_path

    pid = read_pid(pid_path)
    if pid is None or not is_alive(pid_path):
        pid_path.unlink(missing_ok=True)
        app.out.print_error_and_exit("TRAY_NOT_RUNNING", "Tray is not running.")

    # SIGTERM — installMachInterrupt() converts this into clean NSApplication termination
    os.kill(pid, signal.SIGTERM)

    # Wait for process to exit
    deadline = time.monotonic() + _STOP_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        # SIGKILL fallback
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)

    pid_path.unlink(missing_ok=True)
    app.out.print_tray_stopped(TrayStopResult(pid=pid))


def _run_foreground(ctx: typer.Context) -> None:
    """Run the tray in foreground (blocking). Used by the background spawner."""
    app = use_context(ctx)
    cfg = app.cfg
    tray_pid_path = cfg.tray_pid_path

    if is_alive(tray_pid_path):
        app.out.print_error_and_exit("TRAY_ALREADY_RUNNING", "Tray is already running.")

    # Separate DB connection — the tray outlives the CLI context lifecycle
    tray_db = Db(cfg.db_path)
    write_pid_file(tray_pid_path)
    try:
        _run_tray(tray_db, cfg)
    finally:
        tray_pid_path.unlink(missing_ok=True)
        tray_db.close()


def _launch_background(ctx: typer.Context) -> None:
    """Spawn tray in background, verify it started, print PID."""
    app = use_context(ctx)
    cfg = app.cfg

    if is_alive(cfg.tray_pid_path):
        pid = read_pid(cfg.tray_pid_path)
        app.out.print_error_and_exit("TRAY_ALREADY_RUNNING", f"Tray is already running (pid {pid}).")

    pid = spawn_tray(cfg.data_dir)

    # Brief wait to verify the process is alive
    time.sleep(_LAUNCH_VERIFY_SEC)
    if not is_alive(cfg.tray_pid_path):
        app.out.print_error_and_exit("TRAY_LAUNCH_FAILED", "Tray process failed to start.")

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
        _run_foreground(ctx)
    else:
        _launch_background(ctx)
