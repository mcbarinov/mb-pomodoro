"""Structured output for CLI and JSON modes."""

from mm_clikit import DualModeOutput
from rich.table import Table

from mb_pomodoro.core.db import IntervalStatus
from mb_pomodoro.core.results import (
    CancelResult,
    DailyHistoryResult,
    DeleteResult,
    FinishResult,
    HistoryResult,
    PauseResult,
    RaycastInstallResult,
    ReResolveResult,
    RestartResult,
    ResumeResult,
    StartResult,
    StatusActiveResult,
    StatusInactiveResult,
    TrayStartResult,
    TrayStopResult,
)
from mb_pomodoro.time_utils import format_datetime, format_mmss


class Output(DualModeOutput):
    """Handles all CLI output in JSON or human-readable format."""

    def print_started(self, result: StartResult) -> None:
        """Print interval start confirmation."""
        self.output(json_data=result.model_dump(), display_data=f"Pomodoro started: {format_mmss(result.duration_sec)}.")

    def print_paused(self, result: PauseResult) -> None:
        """Print interval pause confirmation."""
        self.output(
            json_data=result.model_dump(),
            display_data=f"Paused. Worked: {format_mmss(result.worked_sec)}, left: {format_mmss(result.remaining_sec)}.",
        )

    def print_resumed(self, result: ResumeResult) -> None:
        """Print interval resume confirmation."""
        self.output(
            json_data=result.model_dump(),
            display_data=f"Resumed. Worked: {format_mmss(result.worked_sec)}, left: {format_mmss(result.remaining_sec)}.",
        )

    def print_cancelled(self, result: CancelResult) -> None:
        """Print interval cancellation confirmation."""
        self.output(json_data=result.model_dump(), display_data=f"Cancelled. Worked: {format_mmss(result.worked_sec)}.")

    def print_deleted(self, result: DeleteResult) -> None:
        """Print interval deletion confirmation."""
        self.output(
            json_data=result.model_dump(),
            display_data=f"Interval {result.interval_id} deleted (was {result.status}, {format_mmss(result.worked_sec)} worked).",
        )

    def print_restarted(self, result: RestartResult) -> None:
        """Print interval restart confirmation."""
        self.output(
            json_data=result.model_dump(),
            display_data=f"Interval {result.interval_id} restarted. Duration: {format_mmss(result.duration_sec)}.",
        )

    def print_re_resolved(self, result: ReResolveResult) -> None:
        """Print interval re-resolution confirmation."""
        self.output(
            json_data=result.model_dump(),
            display_data=f"Interval {result.interval_id} changed from {result.old_resolution} to {result.new_resolution}.",
        )

    def print_finished(self, result: FinishResult) -> None:
        """Print interval resolution confirmation."""
        self.output(
            json_data=result.model_dump(),
            display_data=f"Interval marked as {result.resolution}. Worked: {format_mmss(result.worked_sec)}.",
        )

    def print_history(self, result: HistoryResult) -> None:
        """Print interval history as a table or JSON."""
        json_data: dict[str, object] = {"intervals": [item.model_dump() for item in result.intervals]}
        if not result.intervals:
            self.output(json_data=json_data, display_data="No intervals found.")
            return

        table = Table("Date", "Duration", "Worked", "Status")
        for item in result.intervals:
            table.add_row(
                format_datetime(item.started_at), format_mmss(item.duration_sec), format_mmss(item.worked_sec), str(item.status)
            )
        self.output(json_data=json_data, display_data=table)

    def print_daily_history(self, result: DailyHistoryResult) -> None:
        """Print daily completed counts as a table or JSON."""
        json_data: dict[str, object] = {"days": [item.model_dump() for item in result.days]}
        if not result.days:
            self.output(json_data=json_data, display_data="No completed intervals found.")
            return

        table = Table("Date", "Completed")
        for item in result.days:
            table.add_row(item.date, str(item.completed))
        self.output(json_data=json_data, display_data=table)

    def print_tray_started(self, result: TrayStartResult) -> None:
        """Print tray launch confirmation."""
        self.output(json_data=result.model_dump(), display_data=f"Tray started (pid {result.pid}).")

    def print_tray_stopped(self, result: TrayStopResult) -> None:
        """Print tray stop confirmation."""
        self.output(json_data=result.model_dump(), display_data=f"Tray stopped (pid {result.pid}).")

    def print_raycast_installed(self, result: RaycastInstallResult) -> None:
        """Print Raycast install confirmation."""
        count = len(result.installed)
        if result.refreshed:
            display: str = f"Refreshed {count} Raycast scripts in {result.target_dir}"
        else:
            display = (
                f"Installed {count} Raycast scripts to {result.target_dir}\n"
                "\n"
                "One-time setup in Raycast:\n"
                "  Settings → Extensions → Script Commands → Add Directories\n"
                "  → select the path above"
            )
        self.output(json_data=result.model_dump(), display_data=display)

    def print_status(self, result: StatusActiveResult | StatusInactiveResult, *, short: bool = False) -> None:
        """Print current timer status."""
        if isinstance(result, StatusInactiveResult):
            display_data = (
                f"No active interval · {result.today_completed} today"
                if short
                else f"No active interval. Today: {result.today_completed} completed."
            )
            self.output(json_data={"active": False, "today_completed": result.today_completed}, display_data=display_data)
            return

        if short:
            prefix = "" if result.status == IntervalStatus.RUNNING else f"{str(result.status).capitalize()} · "
            left = format_mmss(result.remaining_sec)
            worked = format_mmss(result.worked_sec)
            display: str = f"{prefix}{left} left · {worked} worked · {result.today_completed} today"
        else:
            display = (
                f"Status:   {result.status}\n"
                f"Duration: {format_mmss(result.duration_sec)}\n"
                f"Worked:   {format_mmss(result.worked_sec)}\n"
                f"Left:     {format_mmss(result.remaining_sec)}\n"
                f"Today:    {result.today_completed} completed"
            )

        self.output(json_data={"active": True, **result.model_dump()}, display_data=display)
