import os
import cv2
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get the source from .env
stream_source = os.getenv("ESP32_STREAM_URL")

# Convert to integer 0 if it's a webcam index
if stream_source and stream_source.isdigit():
    camera_target = int(stream_source)
else:
    camera_target = stream_source

print(f"Attempting to connect to camera source: {camera_target}")

# Start video capture
cap = cv2.VideoCapture(camera_target)

if not cap.isOpened():
    print("Error: Could not open the camera stream. Check your .env file or webcam privacy settings.")
else:
    print("Camera successfully connected! Press 'q' on your keyboard to close the window.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        # Display the live video feed in a window
        cv2.imshow("Webcam Test Window", frame)

        # Break the loop if 'q' key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up and close windows
    cap.release()
    cv2.destroyAllWindows()
    print("Camera test closed successfully.")