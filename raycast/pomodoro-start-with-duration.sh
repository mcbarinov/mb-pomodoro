#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Start Pomodoro…
# @raycast.mode silent
# @raycast.icon 🍅
# @raycast.packageName mb-pomodoro
# @raycast.description Start a Pomodoro with custom duration
# @raycast.argument1 { "type": "text", "placeholder": "Duration (e.g. 45, 10m30s)" }

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro start "$1" 2>&1
