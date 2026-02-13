"""macOS notifications for Pomodoro events."""

import logging
import subprocess  # nosec B404

from mb_pomodoro.db import IntervalStatus

logger = logging.getLogger(__name__)

_SCRIPT = (
    'do shell script "afplay /System/Library/Sounds/Glass.aiff &"\n'
    'display dialog "Your work interval has finished." with title "Pomodoro Complete"'
    ' buttons {"Abandoned", "Completed"} default button "Completed"'
)


def send_notification() -> IntervalStatus | None:
    """Show a macOS dialog for interval resolution and return the user's choice.

    Returns IntervalStatus.COMPLETED, IntervalStatus.ABANDONED, or None on timeout/error.
    """
    try:
        # S603/S607: args are controlled literals, "osascript" is a standard macOS utility
        result = subprocess.run(["osascript", "-e", _SCRIPT], capture_output=True, text=True, check=False, timeout=300)  # noqa: S603, S607  # nosec B603, B607
        stdout = result.stdout.strip()
        if "Completed" in stdout:
            return IntervalStatus.COMPLETED
        if "Abandoned" in stdout:
            return IntervalStatus.ABANDONED
        logger.warning("Unexpected dialog output: %s", stdout)
    except Exception:  # best-effort; failure must not break the timer
        logger.warning("Notification failed", exc_info=True)
    return None
