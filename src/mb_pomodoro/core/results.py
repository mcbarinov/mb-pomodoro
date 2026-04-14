"""Result data types returned by the service layer."""

from pydantic import BaseModel

from mb_pomodoro.core.db import IntervalStatus


class StartResult(BaseModel):
    """Result of a successful interval start."""

    interval_id: int
    duration_sec: int
    started_at: int


class PauseResult(BaseModel):
    """Result of a successful interval pause."""

    interval_id: int
    worked_sec: int
    remaining_sec: int


class ResumeResult(BaseModel):
    """Result of a successful interval resume."""

    interval_id: int
    worked_sec: int
    remaining_sec: int


class CancelResult(BaseModel):
    """Result of a successful interval cancellation."""

    interval_id: int
    worked_sec: int


class DeleteResult(BaseModel):
    """Result of permanently deleting an interval."""

    interval_id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    started_at: int


class RestartResult(BaseModel):
    """Result of restarting a running interval in place."""

    interval_id: int
    duration_sec: int
    started_at: int


class ReResolveResult(BaseModel):
    """Result of changing an interval's resolution."""

    interval_id: int
    old_resolution: IntervalStatus
    new_resolution: IntervalStatus
    worked_sec: int


class FinishResult(BaseModel):
    """Result of resolving a finished interval."""

    interval_id: int
    resolution: IntervalStatus
    worked_sec: int


class StatusActiveResult(BaseModel):
    """Result of a status check when an interval is active."""

    interval_id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    remaining_sec: int
    started_at: int
    today_completed: int


class StatusInactiveResult(BaseModel):
    """Result of a status check when no interval is active."""

    today_completed: int


class HistoryItem(BaseModel):
    """Single interval entry in history output."""

    interval_id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    started_at: int


class HistoryResult(BaseModel):
    """Result of a history query."""

    intervals: list[HistoryItem]


class DailyHistoryItem(BaseModel):
    """Single day entry in daily history output."""

    date: str
    completed: int


class DailyHistoryResult(BaseModel):
    """Result of a daily history query."""

    days: list[DailyHistoryItem]


class TrayStartResult(BaseModel):
    """Result of launching the tray in background."""

    pid: int


class TrayStopResult(BaseModel):
    """Result of stopping the tray."""

    pid: int
