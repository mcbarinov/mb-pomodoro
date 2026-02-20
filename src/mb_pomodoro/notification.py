"""macOS notifications for Pomodoro events."""

import logging

from mm_pymac import show_alert

from mb_pomodoro.db import IntervalStatus

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = 300


def send_notification() -> IntervalStatus | None:
    """Show a macOS dialog for interval resolution and return the user's choice.

    Returns IntervalStatus.COMPLETED, IntervalStatus.ABANDONED, or None on timeout/error.
    """
    result = show_alert(
        "Your work interval has finished.",
        title="Pomodoro Complete",
        buttons=("Abandoned", "Completed"),
        default_button="Completed",
        timeout_sec=_TIMEOUT_SEC,
    )
    if result is None:
        logger.warning("Notification dialog returned no result (timeout or error)")
        return None
    status = {"Completed": IntervalStatus.COMPLETED, "Abandoned": IntervalStatus.ABANDONED}.get(result)
    if status is None:
        logger.warning("Unexpected dialog button: %s", result)
    return status
