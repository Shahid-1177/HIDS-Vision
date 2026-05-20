import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import requests


class NotificationManager:
    """Sends intrusion alerts to Telegram with snapshot attachments."""

    TELEGRAM_API_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str, chat_id: str, max_workers: int = 2) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session = requests.Session()

    def send_intrusion_alert(
        self,
        timestamp: str,
        person_name: str,
        image_path: str,
    ) -> None:
        """Dispatch a background alert and photo for unknown intrusion."""
        message = (
            f"🚨 Intrusion detected!\n"
            f"Timestamp: {timestamp}\n"
            f"Status: Unknown\n"
            f"Person: {person_name}\n"
        )
        logging.info("Sending Telegram alert for unknown person.")
        self.executor.submit(self._send_message_and_photo, message, image_path)

    def _send_message_and_photo(self, message: str, image_path: str) -> None:
        try:
            self._send_text(message)
            self._send_photo(image_path)
            logging.info("Telegram alert sent successfully.")
        except Exception as exc:
            logging.exception("Failed to send Telegram alert: %s", exc)

    def _send_text(self, message: str) -> None:
        url = f"{self.TELEGRAM_API_URL}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        response = self.session.post(url, data=payload, timeout=10)
        response.raise_for_status()

    def _send_photo(self, image_path: str) -> None:
        if not Path(image_path).is_file():
            raise FileNotFoundError(f"Snapshot not found: {image_path}")

        url = f"{self.TELEGRAM_API_URL}/bot{self.bot_token}/sendPhoto"
        with open(image_path, "rb") as image_file:
            files = {"photo": image_file}
            payload = {"chat_id": self.chat_id}
            response = self.session.post(url, data=payload, files=files, timeout=20)
            response.raise_for_status()

    def close(self) -> None:
        self.executor.shutdown(wait=True)
        self.session.close()
