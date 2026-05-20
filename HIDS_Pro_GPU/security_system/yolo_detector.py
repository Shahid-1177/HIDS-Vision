import logging
from typing import List, Tuple

import cv2
from ultralytics import YOLO


class YOLODetector:
    """Wraps YOLOv8 inference and extracts person detections."""

    def __init__(self, weights_path: str = "yolov8n.pt") -> None:
        self.weights_path = weights_path
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            self.model = YOLO(self.weights_path)
            logging.info("YOLO model loaded from %s", self.weights_path)
        except Exception as exc:
            logging.exception("Failed to load YOLO model: %s", exc)
            raise

    def detect_persons(self, frame) -> List[dict]:
        """Run YOLO inference and return person bounding boxes and confidence."""
        try:
            results = self.model(frame, imgsz=640, conf=0.35, verbose=False)
            if not results:
                return []

            detections = []
            result = results[0]
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                return []

            for box, cls, conf in zip(boxes.xyxy, boxes.cls, boxes.conf):
                if int(cls.item()) != 0:
                    continue
                x1, y1, x2, y2 = map(int, box.cpu().numpy().tolist())
                x1 = max(x1, 0)
                y1 = max(y1, 0)
                x2 = max(x2, 0)
                y2 = max(y2, 0)
                detections.append(
                    {
                        "bbox": (x1, y1, x2, y2),
                        "confidence": float(conf.item()),
                    }
                )
            return detections
        except Exception as exc:
            logging.exception("YOLO detection error: %s", exc)
            return []
