import os
import cv2
import face_recognition
import numpy as np
import logging

class FaceRecognitionManager:
    def __init__(self, authorized_dir="authorized_faces", tolerance=0.50):
        self.authorized_dir = authorized_dir
        self.tolerance = tolerance
        self.authorized_encodings = []
        self.authorized_names = []
        
        # --- NEW: Initialize Contrast Enhancer ---
        # Clip limit prevents noise over-amplification; 8x8 grid is standard for faces
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def load_authorized_faces(self):
        """Loads and encodes authorized faces from the directory."""
        if not os.path.exists(self.authorized_dir):
            logging.warning(f"Directory {self.authorized_dir} not found. Creating it.")
            os.makedirs(self.authorized_dir)
            return

        for filename in os.listdir(self.authorized_dir):
            if filename.endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(self.authorized_dir, filename)
                image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    self.authorized_encodings.append(encodings[0])
                    name = os.path.splitext(filename)[0]
                    self.authorized_names.append(name)
                    logging.info(f"Loaded authorized face: {name}")
                else:
                    logging.warning(f"No face found in {filename}. Skipping.")

    def enhance_image(self, face_crop):
        """
        --- NEW: Applies CLAHE to the L channel of LAB color space ---
        This fixes the 'dropping frames' issue in poor lighting without ruining colors.
        """
        if face_crop is None or face_crop.size == 0:
            return face_crop

        # Convert from BGR (OpenCV default) to LAB color space
        lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Apply Contrast Enhancement ONLY to the lightness channel
        l_enhanced = self.clahe.apply(l_channel)

        # Merge back and convert to standard BGR
        merged = cv2.merge((l_enhanced, a_channel, b_channel))
        enhanced_bgr = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        return enhanced_bgr

    def crop_face_region(self, frame, bbox):
        """Crops the face with an optimized 20-pixel padding to catch the whole head."""
        x1, y1, x2, y2 = bbox
        h, w, _ = frame.shape
        
        # --- NEW: Added Padding logic to stabilize recognition ---
        pad = 20
        x1 = max(0, int(x1) - pad)
        y1 = max(0, int(y1) - pad)
        x2 = min(w, int(x2) + pad)
        y2 = min(h, int(y2) + pad)
        
        return frame[y1:y2, x1:x2]

    def verify_face(self, face_crop):
        """
        Verifies the face against authorized encodings.
        Returns: (status, name, face_encoding)
        """
        # Apply the contrast enhancement before the neural network sees it
        enhanced_crop = self.enhance_image(face_crop)
        rgb_crop = cv2.cvtColor(enhanced_crop, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb_crop, model="hog")
        encodings = face_recognition.face_encodings(rgb_crop, locations)

        # If it still can't find a face, return None for the encoding
        if not encodings:
            return "Unknown", "Unknown", None

        # Grab the first face found in the crop
        current_encoding = encodings[0]

        if not self.authorized_encodings:
            return "Unknown", "Unknown", current_encoding

        matches = face_recognition.compare_faces(
            self.authorized_encodings, current_encoding, tolerance=self.tolerance
        )
        distances = face_recognition.face_distance(
            self.authorized_encodings, current_encoding
        )

        if True in matches:
            best_match_index = np.argmin(distances)
            name = self.authorized_names[best_match_index]
            return "Authorized", name, current_encoding

        return "Unknown", "Unknown", current_encoding

    def are_encodings_different(self, encoding1, encoding2, strictness=0.6):
        """
        --- NEW: Math comparison for two Unknown faces ---
        Returns True if the distance between two faces is greater than the strictness.
        """
        if encoding1 is None or encoding2 is None:
            return False
        
        distance = face_recognition.face_distance([encoding1], encoding2)[0]
        return distance > strictness