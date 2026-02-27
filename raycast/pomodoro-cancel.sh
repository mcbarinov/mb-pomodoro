#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Cancel Pomodoro
# @raycast.mode silent
# @raycast.icon ⛔
# @raycast.packageName mb-pomodoro
# @raycast.description Cancel the active Pomodoro interval

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro cancel 2>&1
