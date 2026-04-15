#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Pomodoro Tray
# @raycast.mode silent
# @raycast.icon 🍅
# @raycast.packageName mb-pomodoro
# @raycast.description Launch the menu bar tray icon

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro tray 2>&1
