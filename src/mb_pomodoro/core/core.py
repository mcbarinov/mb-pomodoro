"""Composition root -- owns config, database, and service layer."""

from mb_pomodoro.config import Config
from mb_pomodoro.core.db import Db
from mb_pomodoro.core.service import Service


class Core:
    """Application composition root. Creates and owns all shared resources."""

    def __init__(self, config: Config) -> None:
        """Initialize with config, creating database and service."""
        self.config = config
        self.db = Db(config.db_path)
        self.service = Service(self.db, config)

    def close(self) -> None:
        """Release resources."""
        self.db.close()
