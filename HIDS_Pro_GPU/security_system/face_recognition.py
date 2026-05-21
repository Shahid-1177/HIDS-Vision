import os
import cv2
import numpy as np
import logging
from deepface import DeepFace

# Suppress heavy TensorFlow warning spam in the terminal
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

class FaceRecognitionManager:
    def __init__(self, authorized_dir="authorized_faces", threshold=0.68):
        self.authorized_dir = authorized_dir
        # 0.68 is the standard cosine distance threshold for ArcFace.
        self.threshold = threshold
        self.authorized_encodings = []
        self.authorized_names = []
        self.model_name = "ArcFace"

    def load_authorized_faces(self):
        """Loads and encodes authorized faces using ArcFace embeddings."""
        if not os.path.exists(self.authorized_dir):
            logging.warning(f"Directory {self.authorized_dir} not found. Creating it.")
            os.makedirs(self.authorized_dir)
            return

        for filename in os.listdir(self.authorized_dir):
            if filename.endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(self.authorized_dir, filename)
                
                try:
                    # Extract the 512-dimensional mathematical embedding map
                    embedding_objs = DeepFace.represent(
                        img_path=path, 
                        model_name=self.model_name, 
                        enforce_detection=True
                    )
                    
                    if embedding_objs:
                        embedding = embedding_objs[0]["embedding"]
                        self.authorized_encodings.append(embedding)
                        
                        name = os.path.splitext(filename)[0]
                        self.authorized_names.append(name)
                        logging.info(f"Loaded PRO authorized face (ArcFace): {name}")
                except ValueError:
                    logging.warning(f"No clear face found in {filename} by DeepFace. Skipping.")

    def crop_face_region(self, frame, bbox):
        """Crops the face region out of the main frame with a safe padding buffer."""
        x1, y1, x2, y2 = bbox
        h, w, _ = frame.shape
        
        pad = 20
        x1 = max(0, int(x1) - pad)
        y1 = max(0, int(y1) - pad)
        x2 = min(w, int(x2) + pad)
        y2 = min(h, int(y2) + pad)
        
        return frame[y1:y2, x1:x2]

    def enhance_face(self, face_crop):
        """
        Applies CLAHE enhancement to the face crop to handle shadows/backlighting
        and checks for critical underexposure.
        """
        if face_crop is None or face_crop.size == 0:
            return None, True

        # Convert to LAB color space to isolate lighting
        lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Calculate average illumination (exposure check)
        avg_brightness = np.mean(l_channel)
        if avg_brightness < 45:  # Same safety threshold as the Lite version
            return face_crop, True  # Flag as too dark / underexposed

        # Apply CLAHE to balance out shadows and glare dynamically
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)

        # Merge back channels and map back to standard BGR color space
        enhanced_lab = cv2.merge((cl, a_channel, b_channel))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return enhanced_bgr, False

    def verify_face(self, face_crop):
        """
        Enhances and verifies a live face chip against the authorized database.
        Returns: (status, name, face_encoding)
        """
        if face_crop is None or face_crop.size == 0:
            return "Unknown", "Unknown", None

        # Process through the shadow-killing pipeline
        enhanced_crop, is_underexposed = self.enhance_face(face_crop)
        
        if is_underexposed:
            logging.warning("Face crop is underexposed/silhouette. Skipping AI to prevent false alarms.")
            return "Unknown", "Unknown", None

        try:
            # Feed the enhanced face to ArcFace
            embedding_objs = DeepFace.represent(
                img_path=enhanced_crop, 
                model_name=self.model_name, 
                enforce_detection=False 
            )
            
            if not embedding_objs:
                return "Unknown", "Unknown", None
                
            current_encoding = embedding_objs[0]["embedding"]
            
        except Exception:
            return "Unknown", "Unknown", None

        if not self.authorized_encodings:
            return "Unknown", "Unknown", current_encoding

        # Compare the live vector against all authorized vectors using Cosine Distance
        best_match_name = "Unknown"
        lowest_distance = float("inf")
        best_match_index = -1

        for i, auth_encoding in enumerate(self.authorized_encodings):
            distance = self._cosine_distance(auth_encoding, current_encoding)
            
            if distance < lowest_distance:
                lowest_distance = distance
                best_match_index = i

        # Check if the closest face falls within our match threshold criteria
        if lowest_distance <= self.threshold and best_match_index != -1:
            best_match_name = self.authorized_names[best_match_index]
            return "Authorized", best_match_name, current_encoding

        return "Unknown", "Unknown", current_encoding

    def are_encodings_different(self, encoding1, encoding2, strictness=0.68):
        """Compares two different unknown face vectors to detect distinct intruders."""
        if encoding1 is None or encoding2 is None:
            return False
            
        distance = self._cosine_distance(encoding1, encoding2)
        return distance > strictness

    def _cosine_distance(self, source_rep, test_rep):
        """Calculates the mathematical angle (cosine distance) between two 512D vectors."""
        a = np.array(source_rep)
        b = np.array(test_rep)
        
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        
        if a_norm == 0 or b_norm == 0:
            return 1.0
            
        similarity = np.dot(a, b) / (a_norm * b_norm)
        return 1 - similarity