#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Pomodoro Status
# @raycast.mode compact
# @raycast.icon 📊
# @raycast.packageName mb-pomodoro
# @raycast.description Show current Pomodoro timer status

export PATH="$HOME/.local/bin:$PATH"
mb-pomodoro status --short 2>&1
