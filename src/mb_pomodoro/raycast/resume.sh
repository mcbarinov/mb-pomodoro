#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Resume Pomodoro
# @raycast.mode silent
# @raycast.icon ▶️
# @raycast.packageName mb-pomodoro
# @raycast.description Resume a paused or interrupted Pomodoro interval

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro resume 2>&1
