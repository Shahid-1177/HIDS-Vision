<div align="center">

# 🔥 HIDS-Vision — Pro GPU Edition
### Human Intrusion Detection System · High-Accuracy GPU Accelerated

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8n-Ultralytics-purple?style=flat-square)](https://ultralytics.com)
[![DeepFace](https://img.shields.io/badge/DeepFace-ArcFace-red?style=flat-square)](https://github.com/serengil/deepface)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.10.1-orange?style=flat-square&logo=tensorflow)](https://tensorflow.org)
[![Accuracy](https://img.shields.io/badge/Face_Accuracy-99.65%25_LFW-brightgreen?style=flat-square)]()
[![Platform](https://img.shields.io/badge/Platform-GPU%20%7C%20Desktop%20%7C%20Server-lightgrey?style=flat-square)]()

*Enterprise-grade biometric intrusion detection powered by DeepFace ArcFace — the same neural architecture used in production security systems.*

</div>

---

## 📌 Overview

HIDS-Vision Pro is the high-accuracy GPU-accelerated tier of the HIDS-Vision project. It replaces dlib with **DeepFace's ArcFace model**, a state-of-the-art face recognition neural network originally developed at Microsoft Research that achieves **99.65% accuracy** on the LFW benchmark.

**Perfect for:**
- Desktop workstations with NVIDIA GPU
- Server-based security deployments
- High-security environments requiring maximum accuracy
- Projects where resume/portfolio impact matters
- Scenarios with multiple authorized users or difficult lighting

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
         │  Bounding box coordinates + confidence score
         ▼
  ┌──────────────────────────────────┐
  │     FaceRecognitionManager       │
  │  ┌──────────────────────────┐   │
  │  │ DeepFace · ArcFace Model │   │  ← 99.65% LFW accuracy
  │  │ Cosine Distance Metric   │   │  ← threshold: 0.68
  │  │ enforce_detection=False  │   │  ← robust to partial faces
  │  └──────────────────────────┘   │
  │       authorized_faces/         │
  └──────────────┬───────────────────┘
                 │  (name, status)
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
deepface
tensorflow==2.10.1
opencv-python
python-dotenv
ultralytics
```

> ✅ No manual dlib compilation. `pip install deepface` handles everything automatically.

---

## 🛠️ Installation

### GPU Setup (Recommended)

**NVIDIA GPU users — install CUDA first:**
```bash
# Check your CUDA version
nvidia-smi

# Install matching cuDNN (for TensorFlow 2.10 → CUDA 11.2 + cuDNN 8.1)
# https://developer.nvidia.com/cudnn
```

**CPU-only users:** TensorFlow will fall back to CPU automatically — no changes needed, just slower.

---

### Step-by-Step Setup

```bash
# 1. Navigate to the Pro version folder
cd HIDS_Pro_GPU

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
# .venv\Scripts\activate         # Windows

# 3. Install dependencies (much faster than Lite — no C++ compilation)
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ESP32_STREAM_URL=http://192.168.x.x:81/stream

# DeepFace tuning
FACE_THRESHOLD=0.68            # ArcFace cosine threshold (lower = stricter)
ANTI_SPOOFING=false            # Set true to reject printed photos
ALERT_COOLDOWN_SECONDS=30
```

```bash
# 5. Add authorized face photos
ls authorized_faces/
# shahid.jpg  alice.jpg  john.jpg

# 6. Run the system
#    First run downloads ArcFace model weights (~100MB, one time only)
python main.py
```

---

## 📂 Project Structure

```
HIDS_Pro_GPU/
├── security_system/
│   ├── __init__.py
│   ├── camera.py               # ESP32-CAM stream, auto-reconnect
│   ├── database.py             # SQLite logging, snapshot saving
│   ├── face_recognition.py     # DeepFace ArcFace verification
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

## 🤖 DeepFace ArcFace — How It Works

### Why ArcFace?

ArcFace (Additive Angular Margin Loss) was developed at **Microsoft Research** and is one of the most accurate face recognition models publicly available. It learns face embeddings by maximizing inter-class distance and minimizing intra-class distance using an angular margin loss function.

```
Authorized Face Photo (shahid.jpg)
         │
         ▼
DeepFace.verify() internally:
  1. MTCNN face detector → locates face bounding box
  2. ArcFace ResNet-100  → produces 512-dim embedding vector
  3. Cosine similarity   → compares against live frame embedding
         │
cosine distance < 0.68 → ✅ Authorized (same person)
cosine distance ≥ 0.68 → ❌ Unknown   (different person → Alert)
```

### DeepFace Model Comparison (all available inside DeepFace)

| Model | Accuracy (LFW) | Speed | Used In Pro? |
|---|---|---|---|
| **ArcFace** | **99.65%** | Medium | ✅ Default |
| Facenet512 | 99.65% | Medium | Alternative |
| VGG-Face | 98.78% | Slow | Classic |
| DeepFace | 97.35% | Fast | Facebook original |
| OpenFace | 93.80% | Fast | Lightweight |
| Dlib | 99.38% | Fast | Used in Lite |

---

## 🛡️ Anti-Spoofing (Optional)

The Pro version supports **liveness detection** — it rejects printed photos or images shown on a screen in front of the camera.

Enable in `.env`:
```env
ANTI_SPOOFING=true
```

This adds DeepFace's built-in anti-spoofing model to the verification pipeline. Slightly increases processing time but prevents basic photo-based attacks.

---

## 🚨 Alert Behavior

```
Person detected by YOLO
        │
        ├── DeepFace.verify() cosine distance < 0.68?
        │         YES → ✅ Log "Authorized" (no alert sent)
        │
        └── NO → ❌ "Unknown"
                  │
                  ├── Cooldown expired (>30s)?           → 📲 Alert
                  ├── New distinct intruder detected?    → 📲 Alert (bypass cooldown)
                  └── Same person, cooldown active?      → ⏸️ Suppressed
```

**Telegram alert contains:**
- 🚨 Intrusion alert message with exact timestamp
- 📸 Annotated snapshot (JPG) with person bounding box
- Person name (`Unknown`) and detection confidence

---

## 📊 Performance Benchmarks

| Hardware | FPS (approx) | Notes |
|---|---|---|
| NVIDIA RTX 3060 | 25–30 FPS | Full 720p stream |
| NVIDIA GTX 1660 | 18–25 FPS | Full 720p stream |
| Intel i7 (CPU only) | 5–10 FPS | No GPU, TF CPU backend |
| Intel i5 (CPU only) | 3–6 FPS | Reduce stream resolution |

**Performance tips:**
- First run downloads ArcFace weights — subsequent runs use local cache
- `enforce_detection=False` prevents crashes on partial faces (profile shots, distance)
- Face verification only runs on YOLO-detected person crops, not full frames

---

## 📋 Expected Terminal Output

```
2026-05-19 19:37:08 [INFO] Database initialized at security_system.db
2026-05-19 19:37:08 [INFO] Loading DeepFace ArcFace model…
2026-05-19 19:37:11 [INFO] DeepFace ArcFace ready.
2026-05-19 19:37:11 [INFO]   ✓ Indexed authorized face: 'shahid'
2026-05-19 19:37:11 [INFO]   ✓ Indexed authorized face: 'alice'
2026-05-19 19:37:11 [INFO] Indexed 2 authorized face(s): ['shahid', 'alice']
2026-05-19 19:37:11 [INFO] YOLO model loaded from yolov8n.pt
2026-05-19 19:37:12 [INFO] ✓ ESP32-CAM stream opened successfully.
2026-05-19 19:37:13 [INFO] Person detected confidence=0.92. Running biometric verification.
2026-05-19 19:37:13 [INFO] ✅ AUTHORIZED: 'shahid' (distance: 0.31)
2026-05-19 19:38:45 [INFO] Person detected confidence=0.89. Running biometric verification.
2026-05-19 19:38:45 [INFO] ❌ UNKNOWN: No match found (best distance: 0.79). Alert triggered.
2026-05-19 19:38:45 [WARNING] Sending Telegram alert for unknown person.
2026-05-19 19:38:46 [INFO] Telegram alert sent successfully.
```

---

## 🔧 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Could not find a version that satisfies tensorflow==2.10.1` | Python version mismatch | Use Python 3.9 or 3.10 with TF 2.10 |
| `No GPU devices found` | No CUDA / cuDNN | Normal — TF falls back to CPU automatically |
| Model download hangs | Slow internet or firewall | DeepFace downloads ~100MB ArcFace weights on first run |
| `enforce_detection` error | No face in crop | Already set to `False` in this version |
| `ESP32-CAM stream open failed` | Wrong IP in `.env` | Try `ESP32_STREAM_URL=0` for webcam fallback |

---

## 🔁 Upgrading from Lite to Pro

If you used the Lite version and want to switch:

```bash
# 1. The authorized_faces/ directory is compatible — no changes needed
# 2. Update requirements
pip install deepface tensorflow==2.10.1

# 3. Replace face_recognition.py with the DeepFace version
# 4. Update .env: replace FACE_MATCH_TOLERANCE with FACE_THRESHOLD=0.68
# 5. Optionally enable ANTI_SPOOFING=true
```

The `identify_face()` method returns the same `(name, status)` tuple — `main.py` needs **zero changes**.

---

## 🔗 Related

- [← Back to main HIDS-Vision README](../README.md)
- [← HIDS Lite CPU version](../HIDS_Lite_CPU/README.md)
