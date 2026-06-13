<div align="center">

# 🛡️ HIDS-Vision
### Human Intervention & Intrusion Detection System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple?style=for-the-badge)](https://ultralytics.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?style=for-the-badge&logo=opencv)](https://opencv.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API-blue?style=for-the-badge&logo=telegram)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

*Real-time human intrusion detection using YOLOv8, facial biometric verification, SQLite logging, and instant Telegram alerting.*

</div>

---

## 📌 What is HIDS-Vision?

**HIDS-Vision** is a complete, production-structured security system that streams video from an **ESP32-CAM** (or any webcam), uses **YOLOv8** to detect people in real-time, performs **face biometric verification** to distinguish authorized persons from intruders, logs every event to a **SQLite database**, and fires **Telegram alerts with snapshots** the moment an unknown person is detected.

The project ships in **two tiers** designed for different hardware:

| | HIDS Lite CPU | HIDS Pro GPU |
|---|---|---|
| **Folder** | `HIDS_Lite_CPU/` | `HIDS_Pro_GPU/` |
| **Target Hardware** | Raspberry Pi, Laptop (CPU only) | Desktop / Server with GPU |
| **Face Model** | dlib + `face_recognition` | DeepFace + ArcFace |
| **Accuracy** | ~99.38% (LFW) | ~99.65% (LFW) |
| **Speed** | ⚡ Fast on CPU | 🔥 Fast on GPU |
| **Anti-Spoofing** | ❌ | ✅ Optional |
| **Setup Difficulty** | Medium (dlib compile) | Easy (`pip install deepface`) |
| **Best For** | Edge / IoT deployment | High-accuracy server deployment |

---

## 🏗️ System Architecture

```
ESP32-CAM / Webcam
       │  MJPEG stream
       ▼
 CameraStreamer          ← Handles connect, reconnect, frame buffering
       │  BGR frame
       ▼
  YOLODetector           ← YOLOv8n filters for class 0 (person) only
       │  Bounding box crops
       ▼
FaceRecognitionManager   ← Lite: dlib  |  Pro: DeepFace ArcFace
       │  (name, status)
       ▼
    main.py              ← Orchestrates all modules
   ╱    │    ╲
  ▼     ▼     ▼
DB   Snapshot  Telegram
Log  Save JPG  Alert Bot
```

---

## 🚀 Key Features

- 🎯 **YOLOv8 Person Detection** — only processes frames containing people, maximizing performance
- 🧠 **Biometric Face Verification** — matches faces against an `authorized_faces/` directory
- 🚨 **Smart Alert System** — Telegram text + snapshot photo on every intrusion
- ⏱️ **Cooldown Bypass Logic** — detects a *new* intruder even during active cooldown period
- 💾 **SQLite Event Logging** — every detection event stored with UUID, timestamp, status, image path
- 📸 **Auto Snapshot Saving** — annotated JPG saved per event in `stored_snapshots/`
- 🔁 **Auto-Reconnect** — camera stream drops handled silently with automatic retry
- 🔒 **Secure Config** — all credentials stored in `.env`, never hardcoded

---

## 📁 Repository Structure

```
HIDS-Vision/
│
├── HIDS_Lite_CPU/              # CPU-optimized version (dlib + face_recognition)
│   ├── security_system/
│   │   ├── camera.py
│   │   ├── database.py
│   │   ├── face_recognition.py
│   │   ├── notification.py
│   │   └── yolo_detector.py
│   ├── authorized_faces/       # Add your JPG/PNG face photos here
│   ├── stored_snapshots/       # Auto-created; alert snapshots saved here
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── HIDS_Pro_GPU/               # GPU-accelerated version (DeepFace + ArcFace)
│   ├── security_system/
│   │   ├── camera.py
│   │   ├── database.py
│   │   ├── face_recognition.py  # DeepFace implementation
│   │   ├── notification.py
│   │   └── yolo_detector.py
│   ├── authorized_faces/
│   ├── stored_snapshots/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── ESP_32_WEB_CAM_CODE.ino     # Arduino firmware for ESP32-CAM
├── test_cam.py                 # Quick stream connectivity test
├── .gitignore
└── README.md
```

---

## ⚙️ Environment Setup

Both versions use the same `.env` structure:

```env
# Telegram Bot credentials
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# ESP32-CAM stream URL (or use 0 for webcam testing)
ESP32_STREAM_URL=http://192.168.x.x:81/stream

# Tuning (optional)
FACE_MATCH_TOLERANCE=0.55
ALERT_COOLDOWN_SECONDS=30
```

**Get your Telegram credentials:**
1. Message `@BotFather` → `/newbot` → copy the token
2. Message `@userinfobot` → copy your Chat ID

---

## 📷 ESP32-CAM Setup

1. Open `ESP_32_WEB_CAM_CODE.ino` in Arduino IDE
2. Install board: `ESP32 by Espressif` in Board Manager
3. Set your WiFi SSID and password in the sketch
4. Flash to your ESP32-CAM module
5. Note the IP address shown in Serial Monitor
6. Set `ESP32_STREAM_URL=http://<IP>:81/stream` in `.env`

---

## 🧑‍💼 Adding Authorized Faces

Drop face photos into `authorized_faces/`. The **filename (without extension) becomes the person's name**:

```
authorized_faces/
├── shahid.jpg        → recognized as "shahid"
├── alice.png         → recognized as "alice"
└── john_doe.jpg      → recognized as "john_doe"
```

**Photo requirements:**
- Clear, front-facing headshot
- Good lighting, face unobstructed
- JPG or PNG format
- One face per image

---

## 📊 Alert Logic

```
Person detected by YOLO
        │
        ├── Face matches authorized list?
        │         YES → Log as "Authorized" (no alert)
        │
        └── NO → "Unknown" detected
                  │
                  ├── Cooldown expired (>30s)? → Send alert ✅
                  ├── New distinct intruder?   → Bypass cooldown + Send alert ✅
                  └── Same intruder, cooldown active → Suppress alert ⏸️
```

---

## 🗄️ Database Schema

All events are logged to `security_system.db`:

```sql
CREATE TABLE activity_logs (
    log_id      TEXT PRIMARY KEY,   -- UUID
    timestamp   TEXT NOT NULL,      -- ISO 8601
    status      TEXT NOT NULL,      -- 'Authorized' or 'Unknown'
    person_name TEXT NOT NULL,      -- name or 'Unknown'
    image_path  TEXT NOT NULL       -- path to saved snapshot
);
```

---

## 📦 Quick Start

```bash
# Clone the repo
git clone https://github.com/Shahid-1177/HIDS-Vision.git
cd HIDS-Vision

# Choose your version
cd HIDS_Lite_CPU     # or HIDS_Pro_GPU

# Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Telegram token and ESP32 URL

# Add your face photos to authorized_faces/

# Run
python main.py
```

> See [`HIDS_Lite_CPU/README.md`](HIDS_Lite_CPU/README.md) or [`HIDS_Pro_GPU/README.md`](HIDS_Pro_GPU/README.md) for version-specific installation details.

---

## 🛠️ Tech Stack

| Component | Lite CPU | Pro GPU |
|---|---|---|
| Object Detection | `ultralytics` YOLOv8n | `ultralytics` YOLOv8n |
| Face Recognition | `face_recognition` + dlib | `deepface` + ArcFace |
| Video Capture | `opencv-python` | `opencv-python` |
| Database | SQLite3 (built-in) | SQLite3 (built-in) |
| Alerts | `requests` → Telegram API | `requests` → Telegram API |
| Config | `python-dotenv` | `python-dotenv` |
| Image Processing | `pillow`, `numpy` | `tensorflow` |

---

## 👥 Authors

| Name | GitHub | Role |
|---|---|---|
| Shahid | [@Shahid-1177](https://github.com/Shahid-1177) | Lead Developer |
| Sadiq | [@Sadiqsyed-prog](https://github.com/Sadiqsyed-prog) | ML & Integration |

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
⭐ Star this repo if it helped you &nbsp;|&nbsp; 🍴 Fork it to build your own version
</div>
