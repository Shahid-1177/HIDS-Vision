import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import face_recognition
import numpy as np
from PIL import Image


class FaceRecognitionManager:
    """Loads authorized faces and performs biometric verification safely."""

    def __init__(self, authorized_dir: str = "authorized_faces") -> None:
        self.authorized_dir = Path(authorized_dir)
        self.authorized_encodings: List = []
        self.authorized_names: List[str] = []
        self.authorized_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Core sanitizer — single source of truth for dlib array compliance
    # ------------------------------------------------------------------
    @staticmethod
    def _to_dlib_rgb(image_array: np.ndarray) -> np.ndarray:
        """
        Convert any numpy image array to a pristine, dlib-compatible RGB uint8
        array.  Handles every edge case that causes the dlib error:
          "Unsupported image type, must be 8bit gray or RGB image."

        Pipeline:
          1. Cast to uint8 if needed.
          2. Normalise to exactly 3 channels (handles grayscale and RGBA).
          3. Flatten to raw bytes and rebuild — strips NumPy version headers
             and any non-standard strides from OpenCV views / sub-arrays.
          4. Force a true C-contiguous owned copy via np.ascontiguousarray.
        """
        # ── Step 1: dtype ────────────────────────────────────────────────────
        if image_array.dtype != np.uint8:
            image_array = image_array.astype(np.uint8)

        # ── Step 2: channel normalisation ────────────────────────────────────
        if image_array.ndim == 2:
            # Grayscale → replicate across 3 channels
            image_array = np.stack([image_array] * 3, axis=-1)
        elif image_array.ndim == 3 and image_array.shape[2] == 4:
            # RGBA / BGRA → drop alpha
            image_array = image_array[:, :, :3]
        elif image_array.ndim == 3 and image_array.shape[2] == 1:
            # Single-channel HxWx1 → HxW replicated
            image_array = np.repeat(image_array, 3, axis=2)

        # ── Step 3: raw-byte rebuild (strips numpy metadata / strided views) ─
        raw_bytes = image_array.tobytes()
        rebuilt = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(image_array.shape)

        # ── Step 4: force owned, C-contiguous memory block ──────────────────
        return np.ascontiguousarray(rebuilt, dtype=np.uint8)

    # ------------------------------------------------------------------
    # Authorized face loader
    # ------------------------------------------------------------------
    def load_authorized_faces(self) -> None:
        """
        Scan the authorized_faces directory and build the encoding database.

        Uses PIL instead of cv2.imread so that:
          • EXIF orientation tags are respected automatically.
          • Palette-mode, RGBA, and grayscale images are handled by
            .convert('RGB') before any numpy conversion.
          • No BGR→RGB swap is needed (PIL loads as RGB natively).
        """
        image_files: List[Path] = []
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
            image_files.extend(self.authorized_dir.glob(ext))

        # Deduplicate (glob on case-insensitive FS can yield duplicates)
        image_files = list({f.resolve(): f for f in image_files}.values())

        if not image_files:
            logging.warning(
                "No authorized faces found in '%s'. All detections will be Unknown.",
                self.authorized_dir,
            )
            return

        loaded = 0
        for image_path in image_files:
            try:
                # Path.stem strips the extension cleanly on all platforms
                name = image_path.stem

                # PIL handles EXIF, palette mode, RGBA, grayscale — one call
                pil_image = Image.open(str(image_path)).convert("RGB")
                image_rgb = np.array(pil_image, dtype=np.uint8)

                # Sanitize for dlib
                clean_rgb = self._to_dlib_rgb(image_rgb)

                encodings = face_recognition.face_encodings(clean_rgb)
                if not encodings:
                    logging.warning(
                        "No face detected in authorized image '%s'. "
                        "Ensure the photo shows a clear, front-facing face.",
                        image_path,
                    )
                    continue

                self.authorized_encodings.append(encodings[0])
                self.authorized_names.append(name)
                loaded += 1
                logging.info("Authorized face loaded: %s", name)

            except Exception as exc:
                logging.error(
                    "Error processing authorized face '%s': %s", image_path, exc
                )

        logging.info(
            "Face database ready — %d/%d authorized profile(s) loaded.",
            loaded,
            len(image_files),
        )

    # ------------------------------------------------------------------
    # Frame crop helper
    # ------------------------------------------------------------------
    def crop_face_region(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """Return the person bounding-box region from the frame."""
        x1, y1, x2, y2 = bbox
        return frame[y1:y2, x1:x2]

    # ------------------------------------------------------------------
    # Live verification
    # ------------------------------------------------------------------
    def verify_face(self, person_crop: np.ndarray) -> Tuple[str, str]:
        """
        Identify whether a cropped person image matches an authorized face.

        Returns a (status, name) tuple:
          ("Authorized", "<name>")  — known person
          ("Unknown",    "Unknown") — no match or no face found
        """
        if person_crop is None or person_crop.size == 0:
            logging.debug("Empty person crop — skipping face verification.")
            return "Unknown", "Unknown"

        h, w = person_crop.shape[:2]
        if h < 20 or w < 20:
            logging.debug(
                "Crop too small for reliable detection (%dx%d) — skipping.", w, h
            )
            return "Unknown", "Unknown"

        try:
            # OpenCV frames are BGR; convert to RGB before sanitizing for dlib
            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            clean_crop = self._to_dlib_rgb(rgb_crop)

            face_locs = face_recognition.face_locations(clean_crop)
            if not face_locs:
                logging.info("No face located inside the detected person region.")
                return "Unknown", "Unknown"

            face_encs = face_recognition.face_encodings(clean_crop, face_locs)
            for encoding in face_encs:
                matches = face_recognition.compare_faces(
                    self.authorized_encodings,
                    encoding,
                    tolerance=0.5,
                )
                if any(matches):
                    name = self.authorized_names[matches.index(True)]
                    logging.info("Authorized face recognized: %s", name)
                    return "Authorized", name

            logging.info("Detected face does not match any authorized profile.")
            return "Unknown", "Unknown"

        except Exception as exc:
            logging.error(
                "Unexpected error during face verification processing: %s", exc
            )
            return "Unknown", "Unknown"