#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Start Pomodoro
# @raycast.mode silent
# @raycast.icon 🍅
# @raycast.packageName mb-pomodoro
# @raycast.description Start a new Pomodoro interval (default duration)

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro start 2>&1
