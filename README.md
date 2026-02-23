# mb-pomodoro

macOS-focused Pomodoro timer with a CLI-first workflow. Work intervals only — no break timers.

- CLI is the primary interface.
- Optional GUI integrations (tray icon, Raycast extension) invoke CLI commands as subprocesses with `--json`.
- Persistent state and history in SQLite.
- Background worker process tracks interval completion and sends macOS notifications.

## Timer Algorithm

### Interval Statuses

An interval has one of seven statuses:

| Status | Meaning |
|---|---|
| `running` | Timer is actively counting. Worker is polling. |
| `paused` | Timer is suspended by the user. Worker is not running. |
| `interrupted` | Timer was forcibly stopped by a crash. Worker is not running. |
| `finished` | Full duration elapsed. Awaiting user resolution. |
| `completed` | User confirmed honest work was done. Terminal. |
| `abandoned` | User indicated they did not work. Terminal. |
| `cancelled` | User cancelled before duration elapsed. Terminal. |

### State Transitions

```
                          +-----------+
            start ------> |  running  | <--- resume (paused, interrupted)
                          +-----------+
                         /  |       |  \
                  pause /   |       |   \ cancel
                       v    |       |    v
                +---------+ |       | +-----------+
                | paused  | |       | | cancelled |
                +---------+ |       | +-----------+
                    |        |       |      ^
             cancel +--------+-------+------+
                             |       |
                       crash |       | auto-finish
                    recovery |       |
                             v       v
                     +-------------+ +-----------+
                     | interrupted | | finished  |
                     +-------------+ +-----------+
                                       /       \
                                finish/         \finish
                                     v           v
                               +-----------+ +-----------+
                               | completed | | abandoned |
                               +-----------+ +-----------+
```

Simplified summary:
- `running` -> `paused` (pause), `finished` (auto-finish by worker), `cancelled` (cancel), `interrupted` (crash recovery)
- `paused` -> `running` (resume), `cancelled` (cancel)
- `interrupted` -> `running` (resume), `cancelled` (cancel)
- `finished` -> `completed` (finish completed), `abandoned` (finish abandoned)
- `completed`, `abandoned`, `cancelled` — terminal, no further transitions.

### Time Accounting

Three fields track work time:

- **`worked_sec`** — accumulated completed running time (updated on pause, cancel, auto-finish).
- **`run_started_at`** — timestamp when the current running segment began. `NULL` when not running.
- **`heartbeat_at`** — last worker heartbeat timestamp (~10s interval). Used by crash recovery to credit worked time. `NULL` when not running.

**Effective worked time** (used in status, history, and completion checks):

- If `running`: `worked_sec + (now - run_started_at)`
- Otherwise: `worked_sec`

This design avoids updating the database every second. Only state transitions and periodic heartbeats (~10s) write to the DB.

### Auto-Finish (Timer Worker)

The timer worker is a background process spawned by `start` and `resume`. It polls the database every ~1 second:

1. Fetch the interval row. Exit if status is no longer `running`.
2. Compute effective worked time.
3. When `effective_worked >= duration_sec`:
   - Set `status=finished`, `worked_sec=duration_sec`, `ended_at=now`, `run_started_at=NULL`.
   - Show a macOS dialog (AppleScript) with "Completed" / "Abandoned" buttons (5-minute timeout).
   - If user responds: set `status=<choice>` (`completed` or `abandoned`).
   - If dialog times out or fails: interval stays `finished` — user resolves via `finish` command.
   - Exit worker.

Worker lifecycle:
- Tracked via PID file at `~/.local/mb-pomodoro/timer_worker.pid`.
- Spawned as a detached process (`start_new_session=True`).
- Exits when: interval is no longer running, completion is detected, or an error occurs.
- PID file is removed on exit.

### Crash Recovery

The timer worker writes a heartbeat timestamp (`heartbeat_at`) to the database every ~10 seconds. This enables work time recovery after crashes.

On every CLI command, before executing, the system checks for stale intervals:

1. Fetch the latest interval.
2. If `status=running` but the worker process is not alive:
   - Credit worked time from the last heartbeat: `worked_sec += heartbeat_at - run_started_at` (capped at `duration_sec`).
   - Mark as `interrupted`, clear `run_started_at` and `heartbeat_at`.
   - Insert an `interrupted` event.
   - Remove stale PID file.
3. User must explicitly run `resume` to continue.

Worker liveness check: PID file exists + process is alive (`kill -0`) + process command contains "python" (`ps -p <pid> -o comm=`).

**Limitation**: work time between the last heartbeat and the crash is lost — at most ~10 seconds. If no heartbeat was written (crash within the first few seconds), the current run segment is lost entirely.

### Concurrency

CLI and timer worker may race on writes (e.g., `pause` vs auto-finish). Both use conditional `UPDATE ... WHERE status = 'running'` inside transactions. SQLite serializes these — only one succeeds (`rowcount = 1`), the other gets `rowcount = 0` and handles accordingly.

At most one active interval exists at any time, enforced by a partial unique index.

## Database

Storage engine: SQLite in STRICT mode. Database file: `~/.local/mb-pomodoro/pomodoro.db`.

### Connection Setup

Every connection sets these PRAGMAs before any queries:

```sql
PRAGMA journal_mode = WAL;    -- concurrent CLI + worker access without reader/writer blocking
PRAGMA busy_timeout = 5000;   -- retry on SQLITE_BUSY instead of failing immediately
PRAGMA foreign_keys = ON;     -- enforce foreign key constraints
```

### Schema Migrations

Schema changes are managed via SQLite's built-in `PRAGMA user_version`. Each migration is a Python function in `db.py`, indexed sequentially. On every connection, the app compares the DB's `user_version` to the target version and runs any pending migrations automatically. All migrations are idempotent — safe to re-run.

### Table: `intervals`

One row per work interval. Source of truth for current state.

```sql
CREATE TABLE intervals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    duration_sec   INTEGER NOT NULL,           -- requested duration in seconds
    status         TEXT NOT NULL               -- current lifecycle status
        CHECK(status IN ('running','paused','finished','completed','abandoned','cancelled','interrupted')),
    started_at     INTEGER NOT NULL,           -- initial start time (unix seconds)
    ended_at    INTEGER,                    -- set when finished/cancelled (unix seconds)
    worked_sec     INTEGER NOT NULL DEFAULT 0, -- accumulated active work time (seconds)
    run_started_at INTEGER,                    -- current run segment start (unix seconds), NULL when not running
    heartbeat_at  INTEGER                     -- last worker heartbeat (unix seconds), NULL when not running
) STRICT;
```

| Column | Description |
|---|---|
| `id` | Autoincrement integer, assigned on `start`. |
| `duration_sec` | Requested interval length in seconds (e.g., 1500 for 25 minutes). |
| `status` | Current lifecycle status. See [Interval Statuses](#interval-statuses). |
| `started_at` | Unix timestamp when the interval was first created. Never changes. |
| `ended_at` | Unix timestamp when the interval ended (timer elapsed or cancelled). `NULL` while running/paused. |
| `worked_sec` | Total seconds of actual work. Updated on pause, cancel, and auto-finish. Excludes paused time. |
| `run_started_at` | Unix timestamp of the current running segment's start. Set on `start` and `resume`, cleared (`NULL`) on `pause`, `cancel`, `finish`, and crash recovery. |
| `heartbeat_at` | Unix timestamp of the last worker heartbeat (~10s interval). Used by crash recovery to credit worked time. Cleared on `pause`, `cancel`, `finish`, and crash recovery. |

### Table: `interval_events`

Append-only audit log. One row per state transition.

```sql
CREATE TABLE interval_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    interval_id   INTEGER NOT NULL REFERENCES intervals(id),
    event_type    TEXT NOT NULL
        CHECK(event_type IN ('started','paused','resumed','finished','completed','abandoned','cancelled','interrupted')),
    event_at      INTEGER NOT NULL             -- event time (unix seconds)
) STRICT;
```

Event types map to state transitions:

| Event Type | Trigger |
|---|---|
| `started` | `start` command creates a new interval. |
| `paused` | `pause` command suspends a running interval. |
| `resumed` | `resume` command continues a paused interval. |
| `finished` | Timer worker detects duration elapsed. |
| `completed` | User resolves finished interval as honest work (dialog or `finish` command). |
| `abandoned` | User resolves finished interval as not-worked (dialog or `finish` command). |
| `cancelled` | `cancel` command terminates an active interval. |
| `interrupted` | Crash recovery detects a running interval with a dead worker. |

### Indexes

```sql
-- Enforce at most one active (non-terminal) interval at any time.
-- Prevents concurrent start commands from creating duplicates.
CREATE UNIQUE INDEX idx_one_active
    ON intervals((1)) WHERE status IN ('running','paused','finished','interrupted');

-- Fast event lookup by interval, ordered by time.
CREATE INDEX idx_events_interval_at
    ON interval_events(interval_id, event_at);

-- Fast history queries (most recent first).
CREATE INDEX idx_intervals_started_desc
    ON intervals(started_at DESC);
```

## CLI Commands

All commands support the `--json` flag for machine-readable output.

### Global Options

| Option | Description |
|---|---|
| `--version` | Print version and exit. |
| `--json` | Output results as JSON envelopes. |
| `--data-dir PATH` | Override data directory (default: `~/.local/mb-pomodoro`). Env: `MB_POMODORO_DATA_DIR`. Each directory is an independent instance with its own DB and worker, allowing multiple timers to run simultaneously. |

### `start [duration]`

Start a new work interval.

- `duration` — optional. Formats: `25` (minutes), `25m`, `90s`, `10m30s`. Default: 25 minutes (configurable via `config.toml`).
- Fails if an active interval (running, paused, or finished) already exists.
- Spawns a background timer worker to track completion.

```
$ mb-pomodoro start
Pomodoro started: 25:00.

$ mb-pomodoro start 45
Pomodoro started: 45:00.

$ mb-pomodoro start 10m30s
Pomodoro started: 10:30.
```

### `pause`

Pause the running interval.

- Only valid when status is `running`.
- Accumulates elapsed work time into `worked_sec`, clears `run_started_at`.
- Timer worker exits (no polling while paused).

```
$ mb-pomodoro pause
Paused. Worked: 12:30, left: 12:30.
```

### `resume`

Resume a paused or interrupted interval.

- Only valid when status is `paused` or `interrupted`.
- Sets `run_started_at` to current time, spawns a new timer worker.

```
$ mb-pomodoro resume
Resumed. Worked: 12:30, left: 12:30.
```

### `cancel`

Cancel the active interval.

- Valid from `running`, `paused`, or `interrupted`.
- If running, accumulates the current work segment before cancelling.

```
$ mb-pomodoro cancel
Cancelled. Worked: 08:15.
```

### `finish <resolution>`

Manually resolve a finished interval. Fallback for when the macOS completion dialog was missed or timed out.

- `resolution` — required: `completed` (honest work) or `abandoned` (did not work).
- Only valid when status is `finished`.

```
$ mb-pomodoro finish completed
Interval marked as completed. Worked: 25:00.
```

### `status`

Show current timer status.

```
$ mb-pomodoro status
Status:   running
Duration: 25:00
Worked:   12:30
Left:     12:30

$ mb-pomodoro status
No active interval.
```

### `history [--limit N]`

Show recent intervals. Default limit: 10.

```
$ mb-pomodoro history -n 5
Date              Duration    Worked  Status
----------------  --------  --------  ---------
2026-02-17 14:00     25:00     25:00  completed
2026-02-17 10:30     25:00     15:20  cancelled
2026-02-16 09:00     45:00     45:00  abandoned
```

## Configuration

Optional config file at `~/.local/mb-pomodoro/config.toml`:

```toml
[timer]
default_duration = "25"  # same formats as CLI: "25", "25m", "90s", "10m30s"
```

### Data Directory

Default: `~/.local/mb-pomodoro`. Contents:

| File | Purpose |
|---|---|
| `pomodoro.db` | SQLite database (intervals + events). |
| `timer_worker.pid` | PID of the active timer worker. Exists only while a worker is running. |
| `pomodoro.log` | Rotating log file (1 MB max, 3 backups). |
| `config.toml` | Optional configuration. |

Override with `--data-dir` flag or `MB_POMODORO_DATA_DIR` env variable to run multiple independent instances.

## JSON Output Format

All commands support `--json` for machine-readable output. Envelope:

- Success: `{"ok": true, "data": {<command-specific>}}`
- Error: `{"ok": false, "error": "<error_code>", "message": "<human-readable>"}`

Error codes: `INVALID_DURATION`, `ACTIVE_INTERVAL_EXISTS`, `NOT_RUNNING`, `NOT_RESUMABLE`, `NO_ACTIVE_INTERVAL`, `NOT_FINISHED`, `INVALID_RESOLUTION`, `CONCURRENT_MODIFICATION`.
