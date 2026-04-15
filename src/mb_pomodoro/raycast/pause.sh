#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Pause Pomodoro
# @raycast.mode silent
# @raycast.icon ⏸
# @raycast.packageName mb-pomodoro
# @raycast.description Pause the running Pomodoro interval

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro pause 2>&1
