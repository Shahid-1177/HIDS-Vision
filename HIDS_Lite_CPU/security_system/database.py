import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2


class DatabaseManager:
    """Manages SQLite setup, logging, and snapshot storage."""

    def __init__(self, database_path: str = "security_system.db") -> None:
        self.database_path = database_path
        self.connection: Optional[sqlite3.Connection] = None
        self.snapshots_dir = Path("stored_snapshots")
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking variables to prevent spamming logs every second
        self.last_status: Optional[str] = None
        self.last_person: Optional[str] = None

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
        # CHANGED: log_id is now an auto-incrementing integer instead of a text UUID
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            person_name TEXT NOT NULL,
            image_path TEXT NOT NULL
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_sql)
        self.connection.commit()

    def current_timestamp(self) -> str:
        """Return the current timestamp in ISO 8601 format."""
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def save_snapshot(self, frame, timestamp: str, person_name: str) -> str:
        """Save the current video frame to disk and return the relative path."""
        timestamp_safe = datetime.fromisoformat(timestamp.replace("Z", "")).strftime(
            "%Y%m%d_%H%M%S"
        )
        # CHANGED: Replaced event_uuid with person_name for a cleaner file name
        safe_name = person_name.replace(" ", "_")
        filename = f"{timestamp_safe}_{safe_name}.jpg"
        snapshot_path = self.snapshots_dir / filename
        try:
            success = self._write_jpeg(frame, str(snapshot_path))
            if not success:
                raise IOError("Failed to write snapshot image")
        except Exception as exc:
            logging.exception("Unable to save snapshot: %s", exc)
            raise
        return str(snapshot_path)

    def process_and_log_event(
        self,
        frame,
        timestamp: str,
        status: str,
        person_name: str,
    ) -> bool:
        """
        Evaluate the current state and insert a log ONLY if the state has changed.
        Returns True if a log was written, False if skipped.
        """
        # STATE-CHANGE LOGIC: Check if the current person/status is identical to the last one
        if status == self.last_status and person_name == self.last_person:
            return False  # No change. Skip logging to prevent overflow!

        # If we reach here, the state HAS changed. Update the trackers.
        self.last_status = status
        self.last_person = person_name

        # Save the snapshot ONLY when the state changes
        image_path = self.save_snapshot(frame, timestamp, person_name)

        # CHANGED: Removed log_id from the INSERT statement because SQLite handles it automatically
        insert_sql = """
        INSERT INTO activity_logs (timestamp, status, person_name, image_path)
        VALUES (?, ?, ?, ?);
        """
        try:
            with self.connection:
                self.connection.execute(
                    insert_sql,
                    (timestamp, status, person_name, image_path),
                )
            logging.info("State Changed! Logged event as %s (%s)", status, person_name)
            return True
        except sqlite3.OperationalError as exc:
            logging.exception("Database operational error: %s", exc)
            raise

    @staticmethod
    def _write_jpeg(frame, path: str) -> bool:
        return cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])