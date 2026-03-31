"""Result data types returned by the service layer."""

from dataclasses import dataclass

from mb_pomodoro.db import IntervalStatus


@dataclass(frozen=True, slots=True)
class StartResult:
    """Result of a successful interval start."""

    interval_id: int
    duration_sec: int
    started_at: int


@dataclass(frozen=True, slots=True)
class PauseResult:
    """Result of a successful interval pause."""

    interval_id: int
    worked_sec: int
    remaining_sec: int


@dataclass(frozen=True, slots=True)
class ResumeResult:
    """Result of a successful interval resume."""

    interval_id: int
    worked_sec: int
    remaining_sec: int


@dataclass(frozen=True, slots=True)
class CancelResult:
    """Result of a successful interval cancellation."""

    interval_id: int
    worked_sec: int


@dataclass(frozen=True, slots=True)
class DeleteResult:
    """Result of permanently deleting an interval."""

    interval_id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    started_at: int


@dataclass(frozen=True, slots=True)
class ReResolveResult:
    """Result of changing an interval's resolution."""

    interval_id: int
    old_resolution: IntervalStatus
    new_resolution: IntervalStatus
    worked_sec: int


@dataclass(frozen=True, slots=True)
class FinishResult:
    """Result of resolving a finished interval."""

    interval_id: int
    resolution: IntervalStatus
    worked_sec: int


@dataclass(frozen=True, slots=True)
class StatusActiveResult:
    """Result of a status check when an interval is active."""

    interval_id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    remaining_sec: int
    started_at: int
    today_completed: int


@dataclass(frozen=True, slots=True)
class StatusInactiveResult:
    """Result of a status check when no interval is active."""

    today_completed: int


@dataclass(frozen=True, slots=True)
class HistoryItem:
    """Single interval entry in history output."""

    interval_id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    started_at: int


@dataclass(frozen=True, slots=True)
class HistoryResult:
    """Result of a history query."""

    intervals: list[HistoryItem]


@dataclass(frozen=True, slots=True)
class DailyHistoryItem:
    """Single day entry in daily history output."""

    date: str
    completed: int


@dataclass(frozen=True, slots=True)
class DailyHistoryResult:
    """Result of a daily history query."""

    days: list[DailyHistoryItem]


@dataclass(frozen=True, slots=True)
class TrayStartResult:
    """Result of launching the tray in background."""

    pid: int


@dataclass(frozen=True, slots=True)
class TrayStopResult:
    """Result of stopping the tray."""

    pid: int
