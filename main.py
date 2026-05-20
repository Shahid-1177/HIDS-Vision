import logging
import os
import time  # <-- FIXED: Added for alert cooldown tracking
from dotenv import load_dotenv
from security_system.camera import CameraStreamer
from security_system.database import DatabaseManager
from security_system.face_recognition import FaceRecognitionManager
from security_system.notification import NotificationManager
from security_system.yolo_detector import YOLODetector


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main() -> None:
    setup_logging()
    load_dotenv()

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    stream_url = os.getenv("ESP32_STREAM_URL")

    if not telegram_token or not telegram_chat_id or not stream_url:
        logging.error("Missing required environment variables. Please populate .env.")
        return

    database = DatabaseManager(database_path="security_system.db")
    database.initialize()

    face_manager = FaceRecognitionManager(authorized_dir="authorized_faces")
    face_manager.load_authorized_faces()

    detector = YOLODetector(weights_path="yolov8n.pt")
    notifier = NotificationManager(
        bot_token=telegram_token,
        chat_id=telegram_chat_id,
    )

    streamer = CameraStreamer(stream_url=stream_url)

    # --- FIXED: Cooldown configuration parameters ---
    last_alert_time = 0.0
    ALERT_COOLDOWN_SECONDS = 30.0  # Limits alerts to 1 per 30 seconds
    # ------------------------------------------------

    logging.info("Starting Human Intervention & Intrusion Detection System...")
    try:
        streamer.start_stream()

        while True:
            frame = streamer.read_frame()
            if frame is None:
                logging.warning("Frame not available, retrying...")
                continue

            detections = detector.detect_persons(frame)
            if not detections:
                continue

            for detection in detections:
                bbox = detection["bbox"]
                confidence = detection["confidence"]
                logging.info(
                    f"Person detected with confidence={confidence:.2f}, bbox={bbox}. Running biometric verification."
                )

                crop = face_manager.crop_face_region(frame, bbox)
                status, name = face_manager.verify_face(crop)

                event_uuid = database.generate_uuid()
                timestamp = database.current_timestamp()
                snapshot_path = database.save_snapshot(frame, event_uuid, timestamp)

                # Always log every transaction to the SQLite database
                database.insert_activity_log(
                    log_id=event_uuid,
                    timestamp=timestamp,
                    status=status,
                    person_name=name,
                    image_path=snapshot_path,
                )

                # Trigger notifications for Unknown individuals using a time cooldown fence
                if status == "Unknown":
                    current_time = time.time()
                    if current_time - last_alert_time > ALERT_COOLDOWN_SECONDS:
                        logging.info("Sending Telegram alert for unknown person.")
                        notifier.send_intrusion_alert(
                            timestamp=timestamp,
                            person_name=name,
                            image_path=snapshot_path,
                        )
                        last_alert_time = current_time  # Update timestamp of last alert sent
                    else:
                        time_left = ALERT_COOLDOWN_SECONDS - (current_time - last_alert_time)
                        logging.info(
                            f"Intruder detected, but Telegram alert suppressed. "
                            f"Cooldown active ({time_left:.1f}s remaining)."
                        )

    except KeyboardInterrupt:
        logging.info("Shutdown requested by user.")
    except Exception as exc:
        logging.exception("Unexpected error in main loop: %s", exc)
    finally:
        streamer.close()
        logging.info("System stopped.")


if __name__ == "__main__":
    main()