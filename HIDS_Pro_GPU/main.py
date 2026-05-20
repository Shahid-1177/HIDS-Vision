import logging
import os
import time  
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

    last_alert_time = 0.0
    ALERT_COOLDOWN_SECONDS = 30.0  
    
    # --- NEW: Memory tracker for the last unknown face ---
    last_unknown_encoding = None

    logging.info("Starting HIDS-Vision System...")
    try:
        streamer.start_stream()

        while True:
            frame = streamer.read_frame()
            if frame is None:
                continue

            detections = detector.detect_persons(frame)
            if not detections:
                continue

            for detection in detections:
                bbox = detection["bbox"]
                
                crop = face_manager.crop_face_region(frame, bbox)
                
                # --- NEW: Unpacking the current_encoding for mathematical comparison ---
                status, name, current_encoding = face_manager.verify_face(crop)
                timestamp = database.current_timestamp()

                # Step 1: Database State-Change Logging
                database.process_and_log_event(
                    frame=frame,
                    timestamp=timestamp,
                    status=status,
                    person_name=name,
                )

                # Step 2: Advanced Notification Logic
                if status == "Unknown":
                    current_time = time.time()
                    cooldown_expired = (current_time - last_alert_time > ALERT_COOLDOWN_SECONDS)
                    
                    # --- NEW: Cooldown Bypass Logic ---
                    is_new_intruder = False
                    if current_encoding is not None:
                        if last_unknown_encoding is None:
                            is_new_intruder = True # First time seeing any unknown
                        elif face_manager.are_encodings_different(last_unknown_encoding, current_encoding):
                            is_new_intruder = True # Mathematical proof it is a different person

                    # Trigger alert if the timer is up, OR if a brand new intruder stepped in frame
                    if cooldown_expired or is_new_intruder:
                        
                        if is_new_intruder and not cooldown_expired:
                            logging.warning("🚨 COOLDOWN BYPASSED: A second, distinct intruder was detected!")
                        else:
                            logging.info("Sending Telegram alert for unknown person.")
                        
                        alert_image_path = database.save_snapshot(frame, timestamp, name)
                        
                        notifier.send_intrusion_alert(
                            timestamp=timestamp,
                            person_name=name,
                            image_path=alert_image_path,
                        )
                        
                        # Reset the timer and update the facial memory to the new intruder
                        last_alert_time = current_time  
                        last_unknown_encoding = current_encoding
                        
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