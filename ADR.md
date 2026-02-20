# Architecture Decision Records

## 1. GUI integrations invoke CLI as subprocess

**Context:** The tray menu (and future clients like Raycast) needs to control the timer — start, pause, resume. The business logic (crash recovery, validation, worker spawning, concurrency handling) lives in the CLI commands.

**Decision:** GUI integrations invoke `mb-pomodoro --json <command>` as a subprocess rather than importing and calling Python functions directly.

**Consequences:**
- Single source of truth — CLI commands are the only code path for state transitions.
- No risk of divergent behavior between CLI and GUI.
- Adding a new client (Raycast, Alfred, HTTP API) requires zero changes to core logic.
- Subprocess overhead (~100ms) is negligible for user-initiated actions.
- Tray spawns subprocesses in background threads to keep the NSRunLoop responsive.
