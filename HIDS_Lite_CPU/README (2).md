<div align="center">

# ⚡ HIDS-Vision — Lite CPU Edition
### Human Intrusion Detection System · Edge / CPU Optimized

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8n-Ultralytics-purple?style=flat-square)](https://ultralytics.com)
[![face_recognition](https://img.shields.io/badge/face__recognition-dlib-orange?style=flat-square)](https://github.com/ageitgey/face_recognition)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?style=flat-square&logo=opencv)](https://opencv.org)
[![Platform](https://img.shields.io/badge/Platform-CPU%20%7C%20Raspberry%20Pi%20%7C%20Laptop-lightgrey?style=flat-square)]()

*Lightweight intrusion detection designed to run entirely on CPU — no GPU required. Ideal for Raspberry Pi, edge devices, or any standard laptop.*

</div>

---

## 📌 Overview

HIDS-Vision Lite is the CPU-optimized tier of the HIDS-Vision project. It uses the `face_recognition` library (backed by **dlib's ResNet model**) for biometric verification, which is compiled to run efficiently without a GPU.

**Perfect for:**
- Raspberry Pi 4 / 5 deployments
- Low-power edge devices
- Development and testing on any laptop
- Setups where simplicity and low resource usage matter

---

## 🧠 How It Works

```
[ESP32-CAM / Webcam]
        │
        │  MJPEG stream via HTTP
        ▼
  ┌─────────────┐
  │ CameraStream│  ← cv2.VideoCapture, auto-reconnect, buffer=1
  └──────┬──────┘
         │  BGR frame (numpy array)
         ▼
  ┌─────────────┐
  │ YOLODetector│  ← yolov8n.pt, filters class 0 (person) only
  └──────┬──────┘
         │  Bounding box coordinates
         ▼
  ┌──────────────────────┐
  │ FaceRecognitionManager│  ← dlib HOG + 128-dim ResNet encoding
  │  authorized_faces/   │     compare_faces() vs stored encodings
  └──────────┬───────────┘
             │  (name, status, encoding)
             ▼
  ┌──────────────────────────────────┐
  │           main.py                │
  │  ┌────────┐ ┌────────┐ ┌──────┐ │
  │  │  DB Log│ │Snapshot│ │Alert │ │
  │  │SQLite  │ │  JPG   │ │Tgram │ │
  │  └────────┘ └────────┘ └──────┘ │
  └──────────────────────────────────┘
```

---

## 📦 Dependencies

```txt
opencv-python<4.10
ultralytics
face_recognition
python-dotenv
requests
pillow
numpy<2.0.0
```

> **Note:** `face_recognition` requires `dlib` which **compiles from C++ source**. See installation steps below.

---

## 🛠️ Installation

### Prerequisites

**Ubuntu / Raspberry Pi OS:**
```bash
sudo apt update
sudo apt install -y cmake build-essential libopenblas-dev \
    liblapack-dev libx11-dev libboost-python-dev python3-pip python3-venv
```

**Windows:**
- Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) with C++ workload
- Install [CMake](https://cmake.org/download/)
- Or download a pre-built dlib wheel from [here](https://github.com/z-mahmud-ali/Dlib_Windows_Python3.x)

---

### Step-by-Step Setup

```bash
# 1. Navigate to the Lite version folder
cd HIDS_Lite_CPU

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
#    dlib compilation takes 5–15 minutes on first install
pip install -r requirements.txt

# 4. Copy and fill in your credentials
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ESP32_STREAM_URL=http://192.168.x.x:81/stream

# Optional tuning
FACE_MATCH_TOLERANCE=0.55
ALERT_COOLDOWN_SECONDS=30
```

```bash
# 5. Add authorized face photos
#    Filename = person's name (e.g., shahid.jpg → recognized as "shahid")
ls authorized_faces/
# shahid_1.jpg  shahid_2.jpg  shahid_3.jpg

# 6. Run the system
python main.py
```

---

## 📂 Project Structure

```
HIDS_Lite_CPU/
├── security_system/
│   ├── __init__.py
│   ├── camera.py               # ESP32-CAM stream, auto-reconnect
│   ├── database.py             # SQLite logging, snapshot saving
│   ├── face_recognition.py     # dlib encoding + face matching
│   ├── notification.py         # Telegram Bot API alerts
│   └── yolo_detector.py        # YOLOv8n person detection
├── authorized_faces/           # Drop face photos here
├── stored_snapshots/           # Auto-created; alert snapshots saved here
├── main.py                     # Entry point & orchestration loop
├── requirements.txt
├── .env.example
└── security_system.db          # Auto-created on first run
```

---

## 🧑‍💼 Adding Authorized Persons

1. Take a clear, front-facing headshot photo
2. Name the file after the person: `shahid.jpg`
3. Drop it into `authorized_faces/`
4. Restart the system — encodings are computed at startup

```
authorized_faces/
├── shahid_1.jpg    ← multiple photos of same person improves accuracy
├── shahid_2.jpg
└── alice.jpg
```

---

## 🤖 Face Recognition — How dlib Works

```
Photo in authorized_faces/
         │
         ▼
HOG face detector → finds face bounding box in photo
         │
         ▼
dlib ResNet-34 → outputs 128-dimensional face embedding vector
         │
         ▼ (stored in memory at startup)

Live webcam frame
         │
         ▼
YOLO bbox crop → HOG detector → ResNet-34 → 128-dim vector
         │
         ▼
compare_faces(known_encodings, live_encoding, tolerance=0.55)
         │
Euclidean distance < 0.55 → ✅ Authorized
Euclidean distance ≥ 0.55 → ❌ Unknown → Telegram Alert
```

**Tolerance Guide:**
- `0.4` — very strict, fewer false positives, may miss authorized users
- `0.55` — recommended balance ← default
- `0.6` — dlib default, more lenient

---

## 🚨 Alert Behavior

The Lite version includes **Smart Cooldown Bypass** logic:

```python
# Standard cooldown: 1 alert per 30 seconds
if cooldown_expired:
    send_alert()

# Bypass: fires immediately if a NEW person appears, even mid-cooldown
elif face_manager.are_encodings_different(last_encoding, current_encoding):
    logging.warning("COOLDOWN BYPASSED: Second distinct intruder detected!")
    send_alert()
```

This means if Person A triggers an alert and Person B walks in 5 seconds later — **both get alerted immediately** rather than waiting for the cooldown.

---

## 📊 Performance on Common Hardware

| Device | FPS (approx) | Notes |
|---|---|---|
| Raspberry Pi 4 (4GB) | 3–5 FPS | Reduce resolution to 320×240 |
| Laptop (Intel i5, no GPU) | 8–12 FPS | Standard 640×480 stream |
| Desktop (Intel i7, no GPU) | 15–20 FPS | Full resolution |

**Performance tips:**
- Use `yolov8n.pt` (nano) — smallest and fastest model
- Set ESP32-CAM resolution to SVGA (800×600) or lower
- Face recognition only runs when YOLO detects a person (major optimization)

---

## 📋 Expected Terminal Output

```
2026-05-19 17:37:08 [INFO] Database initialized at security_system.db
2026-05-19 17:37:08 [INFO]   ✓ Authorized face encoded: 'shahid_1'
2026-05-19 17:37:08 [INFO]   ✓ Authorized face encoded: 'shahid_2'
2026-05-19 17:37:08 [INFO] YOLO model loaded from yolov8n.pt
2026-05-19 17:37:08 [INFO] CameraStreamer ready. URL: http://192.168.1.105:81/stream
2026-05-19 17:37:09 [INFO] ✓ ESP32-CAM stream opened successfully.
2026-05-19 17:37:10 [INFO] Person detected confidence=0.90. Running biometric verification.
2026-05-19 17:37:10 [INFO] ✅ AUTHORIZED: 'shahid_1' (distance: 0.38)
2026-05-19 17:38:02 [INFO] Person detected confidence=0.88. Running biometric verification.
2026-05-19 17:38:02 [INFO] ❌ UNKNOWN: distance 0.71 exceeds tolerance 0.55.
2026-05-19 17:38:02 [WARNING] Sending Telegram alert for unknown person.
```

---

## 🔧 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Unsupported image type` | BGR not converted to RGB | Already fixed in this version via `_sanitize_to_rgb()` |
| `dlib install fails` | Missing C++ build tools | Install cmake + build-essential (see Prerequisites) |
| `No face detected in photo` | Poor quality image | Use a clear, front-facing, well-lit headshot |
| `ESP32-CAM stream open failed` | Wrong IP or camera offline | Check IP in `.env`, verify camera is on same WiFi |
| `TELEGRAM_BOT_TOKEN missing` | `.env` not loaded | Ensure `load_dotenv()` is called before `os.getenv()` |

---

## 🔗 Related

- [← Back to main HIDS-Vision README](../README.md)
- [→ HIDS Pro GPU version](../HIDS_Pro_GPU/README.md)
