"""Background timer worker daemon."""

import logging
import os
import time

from mm_clikit import write_pid_file
from mm_pymac import show_alert

from mb_pomodoro.core.core import Core
from mb_pomodoro.core.db import IntervalStatus

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL_SEC = 10
_NOTIFICATION_TIMEOUT_SEC = 300


def _send_notification() -> IntervalStatus | None:
    """Show a macOS dialog for interval resolution and return the user's choice.

    Returns IntervalStatus.COMPLETED, IntervalStatus.ABANDONED, or None on timeout/error.
    """
    result = show_alert(
        "Your work interval has finished.",
        title="Pomodoro Complete",
        buttons=("Abandoned", "Completed"),
        default_button="Completed",
        timeout_sec=_NOTIFICATION_TIMEOUT_SEC,
    )
    if result is None:
        logger.warning("Notification dialog returned no result (timeout or error)")
        return None
    status = {"Completed": IntervalStatus.COMPLETED, "Abandoned": IntervalStatus.ABANDONED}.get(result)
    if status is None:
        logger.warning("Unexpected dialog button: %s", result)
    return status


def run_worker(core: Core, interval_id: int) -> None:
    """Run the timer worker loop. Polls the interval, sends heartbeats, and triggers notification on completion."""
    logger.info("Worker started for interval id=%s pid=%d", interval_id, os.getpid())
    try:
        write_pid_file(core.config.timer_worker_pid_path)
        try:
            last_heartbeat = 0  # Forces immediate heartbeat on first iteration
            while True:
                row = core.service.fetch_interval(interval_id)
                if row is None or row.status != IntervalStatus.RUNNING:
                    logger.info("Worker exiting: interval id=%s no longer running", interval_id)
                    break

                now = int(time.time())

                # Periodic heartbeat for crash recovery
                if now - last_heartbeat >= _HEARTBEAT_INTERVAL_SEC:
                    core.service.update_heartbeat(interval_id, now)
                    last_heartbeat = now

                effective_worked = row.effective_worked(now)
                if effective_worked >= row.duration_sec:
                    if core.service.finish_running(interval_id, row.duration_sec, now):
                        logger.info("Interval finished id=%s duration=%ds", interval_id, row.duration_sec)
                        resolution = _send_notification()
                        if resolution:
                            core.service.resolve(interval_id, resolution, int(time.time()))
                            logger.info("Interval resolved id=%s resolution=%s", interval_id, resolution)
                    else:
                        logger.warning("Finish race lost for interval id=%s", interval_id)
                    break

                time.sleep(1)
        finally:
            core.config.timer_worker_pid_path.unlink(missing_ok=True)
            logger.debug("Worker cleanup: removed PID file")
    except Exception:
        logger.exception("Worker crashed for interval id=%s", interval_id)
        raise
