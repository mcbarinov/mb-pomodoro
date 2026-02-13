"""Background timer worker for active Pomodoro intervals."""

import contextlib
import logging
import os
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path

from mb_pomodoro import db
from mb_pomodoro.config import build_config
from mb_pomodoro.db import IntervalStatus, get_connection
from mb_pomodoro.log import setup_logging
from mb_pomodoro.notification import send_notification

logger = logging.getLogger("mb_pomodoro.timer_worker")  # Hardcoded: __name__ is "__main__" when run via python -m

_HEARTBEAT_INTERVAL_SEC = 10


def is_alive(pid_path: Path) -> bool:
    """Check whether the timer worker process is running by PID file and process liveness."""
    if not pid_path.exists():
        return False

    try:
        pid = int(pid_path.read_text().strip())
    except ValueError, OSError:
        return False

    # Check process exists
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass

    # Verify process is a Python process
    try:
        # S603/S607: args are controlled literals, "ps" is a standard system utility
        result = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True, check=False)  # noqa: S603, S607  # nosec B603, B607
        return "python" in result.stdout.lower()
    except OSError:
        return False


def spawn_timer_worker(interval_id: str, data_dir: Path) -> None:
    """Launch the timer worker as a detached background process."""
    # S603: args are controlled literals, not user input
    subprocess.Popen(  # noqa: S603  # nosec B603
        [sys.executable, "-m", "mb_pomodoro.timer_worker", interval_id, str(data_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def _write_pid_file(pid_path: Path) -> None:
    """Write current PID to the PID file atomically."""
    fd, tmp_path = tempfile.mkstemp(dir=pid_path.parent, prefix=".worker.pid.")
    tmp = Path(tmp_path)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        tmp.replace(pid_path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def _run(interval_id: str, data_dir: Path) -> None:
    """Poll the database and complete the interval when time is up."""
    cfg = build_config(data_dir)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(cfg.log_path)
    logger.info("Worker started for interval id=%s pid=%d", interval_id, os.getpid())
    try:
        _write_pid_file(cfg.pid_path)
        try:
            conn = get_connection(cfg.db_path)
            last_heartbeat = 0  # Forces immediate heartbeat on first iteration
            try:
                while True:
                    row = db.fetch_interval(conn, interval_id)
                    if row is None or row.status != IntervalStatus.RUNNING:
                        logger.info("Worker exiting: interval id=%s no longer running", interval_id)
                        break

                    # Compute effective worked time
                    now = int(time.time())

                    # Periodic heartbeat for crash recovery
                    if now - last_heartbeat >= _HEARTBEAT_INTERVAL_SEC:
                        db.update_heartbeat(conn, interval_id, now)
                        last_heartbeat = now

                    effective_worked = row.effective_worked(now)
                    if effective_worked >= row.duration_sec:
                        if db.finish_interval(conn, interval_id, row.duration_sec, now):
                            logger.info("Interval finished id=%s duration=%ds", interval_id, row.duration_sec)
                            resolution = send_notification()
                            if resolution:
                                db.resolve_interval(conn, interval_id, resolution, int(time.time()))
                                logger.info("Interval resolved id=%s resolution=%s", interval_id, resolution)
                        else:
                            logger.warning("Finish race lost for interval id=%s", interval_id)
                        break

                    time.sleep(1)
            finally:
                conn.close()
        finally:
            cfg.pid_path.unlink(missing_ok=True)
            logger.debug("Worker cleanup: removed PID file")
    except Exception:
        logger.exception("Worker crashed for interval id=%s", interval_id)
        raise


if __name__ == "__main__":
    _run(sys.argv[1], Path(sys.argv[2]))
