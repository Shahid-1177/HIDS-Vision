# camera.py — complete fixed version
import logging
import os
import time
from typing import Optional

import cv2
from dotenv import load_dotenv

load_dotenv()  # safety net in case main.py forgets


class CameraStreamer:
    """Manages connection to the ESP32-CAM stream with automatic reconnect."""

    def __init__(
        self,
        stream_url: Optional[str] = None,  # ← now has a default
        reconnect_delay: float = 5.0,
    ) -> None:
        # If no URL passed → read from .env automatically
        self.stream_url = stream_url or os.getenv("ESP32_STREAM_URL")
        self.reconnect_delay = reconnect_delay
        self.capture: Optional[cv2.VideoCapture] = None

        # Fail early with a clear message instead of a cryptic OpenCV error
        if not self.stream_url:
            raise ValueError(
                "No stream URL provided.\n"
                "Either pass stream_url= or set ESP32_STREAM_URL in .env"
            )

        logging.info("CameraStreamer ready. URL: %s", self.stream_url)

    def start_stream(self) -> None:
        """Open the video stream from the ESP32 camera."""
        self._open_stream()

    def _open_stream(self) -> None:
        """Try ESP32 stream first, fall back to webcam for local testing."""
        logging.info("Connecting to: %s", self.stream_url)

        self.capture = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.capture.isOpened():
            logging.info("✓ ESP32-CAM stream opened successfully.")
            return

        # -------------------------------------------------------
        # ESP32 unreachable — helpful debug checklist
        # -------------------------------------------------------
        logging.warning(
            "ESP32-CAM not reachable at: %s\n"
            "  Checklist:\n"
            "    [1] Is ESP32-CAM powered on?\n"
            "    [2] Is it on the same WiFi as this PC?\n"
            "    [3] Is the IP address correct in .env?\n"
            "    [4] Try opening the URL in your browser first.\n"
            "  → Falling back to local webcam (index 0) for testing...",
            self.stream_url,
        )

        # Fallback: use laptop webcam so you can test without hardware
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.capture.isOpened():
            logging.info("✓ Fallback: using local webcam for testing.")
            return

        # Both failed
        raise ConnectionError(
            f"Could not open ESP32 stream ({self.stream_url}) "
            "or local webcam.\n"
            "Check your .env ESP32_STREAM_URL value."
        )

    def read_frame(self):
        """Read a single frame and reconnect automatically on failure."""
        if self.capture is None or not self.capture.isOpened():
            try:
                self._open_stream()
            except Exception as exc:
                logging.error("Reconnect failed: %s", exc)
                return None

        success, frame = self.capture.read()
        if not success or frame is None:
            logging.warning("Lost camera frame. Reconnecting in %ss...",
                            self.reconnect_delay)
            self.close()
            time.sleep(self.reconnect_delay)
            return None

        return frame

    def close(self) -> None:
        """Release the camera resource."""
        if self.capture is not None:
            self.capture.release()
            self.capture = None
            logging.info("ESP32-CAM stream closed.")