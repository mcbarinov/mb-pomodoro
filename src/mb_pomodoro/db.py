"""Database connection, schema management, and query/mutation functions."""

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from mb_pomodoro.time_utils import start_of_day

logger = logging.getLogger(__name__)

# --- Migrations ---


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Create initial schema: intervals + interval_events tables and indexes."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS intervals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duration_sec INTEGER NOT NULL,
            status TEXT NOT NULL
                CHECK(status IN ('running','paused','finished','completed','abandoned','cancelled','interrupted')),
            started_at INTEGER NOT NULL,
            ended_at INTEGER,
            worked_sec INTEGER NOT NULL DEFAULT 0,
            run_started_at INTEGER,
            heartbeat_at INTEGER
        ) STRICT;

        CREATE TABLE IF NOT EXISTS interval_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interval_id INTEGER NOT NULL REFERENCES intervals(id),
            event_type TEXT NOT NULL
                CHECK(event_type IN ('started','paused','resumed','finished','completed','abandoned','cancelled','interrupted')),
            event_at INTEGER NOT NULL
        ) STRICT;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active
            ON intervals((1)) WHERE status IN ('running','paused','finished','interrupted');
        CREATE INDEX IF NOT EXISTS idx_events_interval_at
            ON interval_events(interval_id, event_at);
        CREATE INDEX IF NOT EXISTS idx_intervals_started_desc
            ON intervals(started_at DESC);
    """)


# Indexed by position: _MIGRATIONS[0] = v1, _MIGRATIONS[1] = v2, etc.
# user_version=0 means no migrations applied.
_MIGRATIONS: tuple[Callable[[sqlite3.Connection], None], ...] = (_migrate_v1,)


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run all pending schema migrations based on PRAGMA user_version."""
    current_version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    for i, migrate_fn in enumerate(_MIGRATIONS):
        target_version = i + 1
        if current_version < target_version:
            migrate_fn(conn)
            conn.execute(f"PRAGMA user_version = {target_version}")
            logger.info("Applied migration v%d (%s)", target_version, migrate_fn.__doc__)


class IntervalStatus(StrEnum):
    """Interval lifecycle status."""

    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


ACTIVE_STATUSES = frozenset(
    {
        IntervalStatus.RUNNING,
        IntervalStatus.PAUSED,
        IntervalStatus.INTERRUPTED,
        IntervalStatus.FINISHED,
    }
)


class EventType(StrEnum):
    """Interval event type for the audit log."""

    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    FINISHED = "finished"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class IntervalRow:
    """Interval row projection."""

    id: int
    status: IntervalStatus
    duration_sec: int
    worked_sec: int
    run_started_at: int | None
    started_at: int
    heartbeat_at: int | None

    def effective_worked(self, now: int) -> int:
        """Compute actual worked time including the current running segment."""
        if self.status == IntervalStatus.RUNNING and self.run_started_at is not None:
            return min(self.worked_sec + (now - self.run_started_at), self.duration_sec)
        return self.worked_sec


# --- Helpers ---

_SELECT_INTERVAL = "SELECT id, status, duration_sec, worked_sec, run_started_at, started_at, heartbeat_at FROM intervals"


def _to_interval_row(row: tuple[int, str, int, int, int | None, int, int | None]) -> IntervalRow:
    """Convert a raw SQL row tuple to an IntervalRow with enum conversion."""
    return IntervalRow(
        id=row[0],
        status=IntervalStatus(row[1]),
        duration_sec=row[2],
        worked_sec=row[3],
        run_started_at=row[4],
        started_at=row[5],
        heartbeat_at=row[6],
    )


class Db:
    """Database access object holding a SQLite connection."""

    def __init__(self, db_path: Path) -> None:
        """Open a SQLite connection with WAL mode, busy timeout, foreign keys, and run pending migrations.

        Args:
            db_path: Path to the SQLite database file.

        """
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA foreign_keys = ON")
        _run_migrations(self._conn)

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    # --- Private ---

    def _insert_event(self, interval_id: int, event_type: EventType, event_at: int) -> None:
        """Insert a row into interval_events."""
        self._conn.execute(
            "INSERT INTO interval_events (interval_id, event_type, event_at) VALUES (?, ?, ?)",
            (interval_id, event_type, event_at),
        )

    # --- Queries ---

    def fetch_latest_interval(self) -> IntervalRow | None:
        """Return the most recently started interval, or None."""
        row = self._conn.execute(_SELECT_INTERVAL + " ORDER BY started_at DESC LIMIT 1").fetchone()
        return _to_interval_row(row) if row else None

    def fetch_interval(self, interval_id: int) -> IntervalRow | None:
        """Return an interval by id, or None."""
        row = self._conn.execute(_SELECT_INTERVAL + " WHERE id = ?", (interval_id,)).fetchone()
        return _to_interval_row(row) if row else None

    def fetch_history(self, limit: int) -> list[IntervalRow]:
        """Return the most recent intervals ordered by started_at DESC."""
        rows = self._conn.execute(_SELECT_INTERVAL + " ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return [_to_interval_row(row) for row in rows]

    def fetch_daily_completed(self, limit: int) -> list[tuple[str, int]]:
        """Return daily completed counts (date, count) ordered by date DESC, days with >0 only."""
        rows = self._conn.execute(
            "SELECT date(started_at, 'unixepoch', 'localtime') AS day, COUNT(*) AS cnt"
            " FROM intervals WHERE status = 'completed'"
            " GROUP BY day ORDER BY day DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def count_today_completed(self, now: int) -> int:
        """Count intervals completed today (local midnight to now)."""
        today_start = start_of_day(now)
        row = self._conn.execute(
            "SELECT COUNT(*) FROM intervals WHERE started_at >= ? AND status = 'completed'",
            (today_start,),
        ).fetchone()
        return int(row[0])

    # --- Mutations ---

    def insert_interval(self, duration_sec: int, now: int) -> int | None:
        """Create a new running interval with 'started' event. Return the new row ID, or None on IntegrityError."""
        try:
            cursor = self._conn.execute(
                "INSERT INTO intervals (duration_sec, status, started_at, worked_sec, run_started_at)"
                " VALUES (?, 'running', ?, 0, ?)",
                (duration_sec, now, now),
            )
            interval_id = cursor.lastrowid
            if interval_id is None:
                self._conn.rollback()
                return None
            self._insert_event(interval_id, EventType.STARTED, now)
            self._conn.commit()
        except sqlite3.IntegrityError:
            return None
        return interval_id

    def finish_interval(self, interval_id: int, duration_sec: int, now: int) -> bool:
        """Mark running interval as finished (awaiting resolution). Return False if rowcount == 0."""
        cursor = self._conn.execute(
            "UPDATE intervals SET status = 'finished', worked_sec = ?, ended_at = ?,"
            " run_started_at = NULL, heartbeat_at = NULL WHERE id = ? AND status = 'running'",
            (duration_sec, now, interval_id),
        )
        if cursor.rowcount == 0:
            self._conn.rollback()
            return False
        self._insert_event(interval_id, EventType.FINISHED, now)
        self._conn.commit()
        return True

    def resolve_interval(self, interval_id: int, resolution: IntervalStatus, now: int) -> bool:
        """Resolve a finished interval as 'completed' or 'abandoned'. Return False if rowcount == 0.

        Note: does not update ended_at — that records when the timer elapsed (set by finish_interval),
        not when the user made a resolution decision.
        """
        cursor = self._conn.execute(
            "UPDATE intervals SET status = ? WHERE id = ? AND status = 'finished'",
            (resolution, interval_id),
        )
        if cursor.rowcount == 0:
            self._conn.rollback()
            return False
        self._insert_event(interval_id, EventType(resolution), now)
        self._conn.commit()
        return True

    def pause_interval(self, interval_id: int, worked_sec: int, now: int) -> bool:
        """Pause a running interval. Return False if no running interval was updated."""
        cursor = self._conn.execute(
            "UPDATE intervals SET status = 'paused', worked_sec = ?, run_started_at = NULL, heartbeat_at = NULL"
            " WHERE id = ? AND status = 'running'",
            (worked_sec, interval_id),
        )
        if cursor.rowcount == 0:
            self._conn.rollback()
            return False
        self._insert_event(interval_id, EventType.PAUSED, now)
        self._conn.commit()
        return True

    def resume_interval(self, interval_id: int, now: int) -> bool:
        """Resume a paused interval. Return False if no paused interval was updated."""
        cursor = self._conn.execute(
            "UPDATE intervals SET status = 'running', run_started_at = ? WHERE id = ? AND status IN ('paused', 'interrupted')",
            (now, interval_id),
        )
        if cursor.rowcount == 0:
            self._conn.rollback()
            return False
        self._insert_event(interval_id, EventType.RESUMED, now)
        self._conn.commit()
        return True

    def cancel_interval(self, interval_id: int, worked_sec: int, now: int) -> bool:
        """Cancel a running or paused interval. Return False if no active interval was updated."""
        cursor = self._conn.execute(
            "UPDATE intervals SET status = 'cancelled', worked_sec = ?, ended_at = ?,"
            " run_started_at = NULL, heartbeat_at = NULL WHERE id = ? AND status IN ('running', 'paused', 'interrupted')",
            (worked_sec, now, interval_id),
        )
        if cursor.rowcount == 0:
            self._conn.rollback()
            return False
        self._insert_event(interval_id, EventType.CANCELLED, now)
        self._conn.commit()
        return True

    def update_heartbeat(self, interval_id: int, now: int) -> None:
        """Update heartbeat timestamp for a running interval."""
        self._conn.execute("UPDATE intervals SET heartbeat_at = ? WHERE id = ? AND status = 'running'", (now, interval_id))
        self._conn.commit()

    def recover_running_interval(self, interval_id: int, now: int) -> bool:
        """Mark running interval as interrupted, credit worked time from heartbeat, and insert 'interrupted' event.

        Uses heartbeat_at to recover work time accumulated before the crash.
        Falls back to no credit if heartbeat_at is NULL (no heartbeat was written).
        Return False if no running interval was updated.
        """
        cursor = self._conn.execute(
            "UPDATE intervals SET status = 'interrupted',"
            " worked_sec = CASE"
            "   WHEN heartbeat_at IS NOT NULL AND run_started_at IS NOT NULL"
            "   THEN MIN(worked_sec + (heartbeat_at - run_started_at), duration_sec)"
            "   ELSE worked_sec END,"
            " run_started_at = NULL, heartbeat_at = NULL"
            " WHERE id = ? AND status = 'running'",
            (interval_id,),
        )
        if cursor.rowcount == 0:
            self._conn.rollback()
            return False
        self._insert_event(interval_id, EventType.INTERRUPTED, now)
        self._conn.commit()
        return True
