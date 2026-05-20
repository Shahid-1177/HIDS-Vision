import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import cv2


class DatabaseManager:
    """Manages SQLite setup, logging, and snapshot storage."""

    def __init__(self, database_path: str = "security_system.db") -> None:
        self.database_path = database_path
        self.connection: Optional[sqlite3.Connection] = None
        self.snapshots_dir = Path("stored_snapshots")
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Initialize SQLite database and required table."""
        try:
            self.connection = sqlite3.connect(
                self.database_path,
                timeout=30,
                check_same_thread=False,
            )
            self.connection.execute("PRAGMA journal_mode=WAL;")
            self.connection.execute("PRAGMA foreign_keys=ON;")
            self._create_tables()
            logging.info("Database initialized at %s", self.database_path)
        except sqlite3.Error as exc:
            logging.exception("Failed to initialize database: %s", exc)
            raise

    def _create_tables(self) -> None:
        """Create activity_logs table if it does not exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            person_name TEXT NOT NULL,
            image_path TEXT NOT NULL
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)
        self.connection.commit()

    def generate_uuid(self) -> str:
        """Generate a new UUID for an event."""
        return str(uuid4())

    def current_timestamp(self) -> str:
        """Return the current timestamp in ISO 8601 format."""
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def save_snapshot(self, frame, event_uuid: str, timestamp: str) -> str:
        """Save the current video frame to disk and return the relative path."""
        timestamp_safe = datetime.fromisoformat(timestamp.replace("Z", "")).strftime(
            "%Y%m%d_%H%M%S"
        )
        filename = f"{timestamp_safe}_{event_uuid}.jpg"
        snapshot_path = self.snapshots_dir / filename
        try:
            success = self._write_jpeg(frame, str(snapshot_path))
            if not success:
                raise IOError("Failed to write snapshot image")
        except Exception as exc:
            logging.exception("Unable to save snapshot: %s", exc)
            raise
        return str(snapshot_path)

    def insert_activity_log(
        self,
        log_id: str,
        timestamp: str,
        status: str,
        person_name: str,
        image_path: str,
    ) -> None:
        """Insert a detection event into the database."""
        insert_sql = """
        INSERT INTO activity_logs (log_id, timestamp, status, person_name, image_path)
        VALUES (?, ?, ?, ?, ?);
        """
        try:
            with self.connection:
                self.connection.execute(
                    insert_sql,
                    (log_id, timestamp, status, person_name, image_path),
                )
            logging.info("Logged event %s as %s", log_id, status)
        except sqlite3.IntegrityError:
            logging.warning("Duplicate log_id detected: %s", log_id)
        except sqlite3.OperationalError as exc:
            logging.exception("Database operational error: %s", exc)
            raise

    @staticmethod
    def _write_jpeg(frame, path: str) -> bool:
        return cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
