# Raycast Integration

[Script Commands](https://github.com/raycast/script-commands) ship with `mb-pomodoro` for controlling the timer from Raycast's search bar.

## Available Commands

| Command | Description |
|---|---|
| Start Pomodoro | Start with default duration |
| Start Pomodoro... | Start with custom duration (prompts for input) |
| Pause Pomodoro | Pause the running interval |
| Resume Pomodoro | Resume a paused or interrupted interval |
| Cancel Pomodoro | Cancel the active interval |
| Pomodoro Status | Show current timer status |
| Pomodoro Tray | Launch the menu bar tray icon |

## Setup (end users)

1. Install `mb-pomodoro` via `uv tool install mb-pomodoro` (ensures the binary lands in `~/.local/bin/`).
2. Run:
   ```
   mb-pomodoro raycast install
   ```
   This writes the scripts to `<data_dir>/raycast/` (default `~/.local/mb-pomodoro/raycast/`) with the absolute binary path and `--data-dir` baked in. Pass a positional argument to choose a different directory, and `--force` to overwrite existing files.
3. In Raycast: open **Settings → Extensions → Script Commands → Add Directories**, then select the path printed by the install command. This is a one-time step.

After upgrades (`uv tool upgrade mb-pomodoro`), re-run `mb-pomodoro raycast install --force` to refresh the scripts. Raycast automatically picks up changes in the existing directory — no additional action needed.

Action commands (start, pause, resume, cancel) show a brief HUD notification with the result. Status shows a compact single-line summary.

## Setup (contributors)

The source-of-truth scripts live at `src/mb_pomodoro/raycast/*.sh` inside the repo and are shipped as package data. On a dev machine point Raycast directly at that directory — edits are picked up live without re-running `raycast install`. The scripts rely on `mb-pomodoro` being on `PATH` (via `uv tool install mb-pomodoro` from the repo or a published version).
