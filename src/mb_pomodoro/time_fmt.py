"""Time parsing and formatting utilities."""

import re
from datetime import UTC, datetime

_DURATION_RE = re.compile(r"(?:(\d+)m)?(?:(\d+)s)?")


def parse_duration(raw: str) -> int | None:
    """Parse a duration string into seconds.

    Supported formats: '25' (minutes), '25m', '90s', '10m30s'.
    Returns None on invalid input.
    """
    if raw.isdigit():
        return int(raw) * 60

    m = _DURATION_RE.fullmatch(raw)
    if not m or not any(m.groups()):
        return None

    minutes = int(m.group(1) or 0)
    seconds = int(m.group(2) or 0)
    return minutes * 60 + seconds


def format_mmss(seconds: int) -> str:
    """Format seconds as MM:SS."""
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def format_datetime(unix_ts: int) -> str:
    """Format unix timestamp as 'YYYY-MM-DD HH:MM' in local time."""
    dt = datetime.fromtimestamp(unix_ts, tz=UTC).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")
