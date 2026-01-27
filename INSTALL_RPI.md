# 🍓 MEMO - Raspberry Pi Installation Guide

This guide helps you install MEMO on Raspberry Pi (Tested on Pi 4/5 with Raspberry Pi OS 64-bit).

## Prerequisites

- Raspberry Pi 4 (4GB+ recommended) or Pi 5
- Raspberry Pi OS 64-bit (Bookworm recommended)
- Python 3.11+
- At least 8GB free disk space

---

## Step 1: Update System & Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y cmake build-essential pkg-config
sudo apt install -y libatlas-base-dev libopenblas-dev

# Install audio dependencies
sudo apt install -y portaudio19-dev python3-pyaudio
sudo apt install -y espeak espeak-ng libespeak-dev

# Install camera support
sudo apt install -y libcamera-dev libcap-dev
```

---

## Step 2: Clone MEMO

```bash
cd ~
git clone https://github.com/jay7-tech/memo.git
cd memo
```

---

## Step 3: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 4: Install PyTorch for Raspberry Pi

PyTorch doesn't have official ARM wheels on PyPI. Use **piwheels** or install from source:

### Option A: Use PyTorch Lite (Recommended for Pi 4)

```bash
# Install PyTorch from piwheels (pre-built for ARM)
pip install torch torchvision --index-url https://www.piwheels.org/simple
```

### Option B: Install from PyTorch's ARM builds

For Raspberry Pi OS 64-bit:

```bash
# Check your Python version first
python --version

# For Python 3.11 on Pi OS 64-bit (Bookworm):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Option C: Skip PyTorch (Lite Mode)

If PyTorch installation fails, you can run MEMO in **lite mode** without face recognition:

```bash
# Set environment variable to disable PyTorch features
export MEMO_LITE_MODE=1
```

---

## Step 5: Install OpenCV for Raspberry Pi

```bash
# Install headless OpenCV (smaller, no GUI dependencies)
pip install opencv-python-headless>=4.8.0

# Alternative: Use system OpenCV
sudo apt install -y python3-opencv
```

---

## Step 6: Install Remaining Dependencies

```bash
pip install -r requirements_rpi.txt
```

---

## Step 7: Install YOLO (Ultralytics) for Raspberry Pi

```bash
# Ultralytics works on Pi but may be slow
pip install ultralytics

# For better performance, use YOLOv8 nano models
# The project already uses yolov8n.pt (nano version)
```

---

## Step 8: Download Vosk Model (Offline Speech Recognition)

```bash
# Create models directory
mkdir -p models/vosk

# Download small English model (40MB)
cd models/vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-en
cd ../..
```

---

## Step 9: Configure for Raspberry Pi

Edit `config.json` to optimize for Pi:

```json
{
  "camera": {
    "device_id": 0,
    "width": 640,
    "height": 480,
    "fps": 15
  },
  "perception": {
    "enable_emotion_detection": false,
    "enable_pose_tracking": false,
    "enable_face_recognition": true,
    "object_detection_interval": 3.0
  },
  "voice": {
    "enable_voice_input": true,
    "wake_word": "hey memo",
    "speech_timeout": 5.0
  }
}
```

---

## Step 10: Run MEMO

```bash
# Activate virtual environment (if not already)
source venv/bin/activate

# Run MEMO
python main.py
```

---

## 🔧 Troubleshooting

### Error: "No matching distribution found for torch"

This means PyTorch ARM wheels aren't available. Solutions:

1. **Try piwheels**: `pip install torch --index-url https://www.piwheels.org/simple`
2. **Use CPU-only**: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
3. **Skip torch**: Run in lite mode without face recognition

### Error: "Could not find a version that satisfies mediapipe"

MediaPipe has limited ARM support. Alternative:

```bash
# Skip mediapipe - hand gesture features won't work
# Or try building from source (advanced)
```

### Error: PyAudio installation fails

```bash
sudo apt install -y portaudio19-dev python3-pyaudio
pip install pyaudio
```

### Camera not detected

```bash
# Enable camera interface
sudo raspi-config
# Navigate: Interface Options > Camera > Enable

# Test camera
libcamera-hello --list-cameras

# If using USB webcam
ls /dev/video*
```

### Performance is slow

1. Use **YOLOv8 nano** models (already default)
2. Lower camera resolution to 480p
3. Increase detection intervals in config
4. Disable features you don't need

---

## 📊 Raspberry Pi Performance Tips

| Feature | Pi 4 (4GB) | Pi 5 |
|---------|------------|------|
| Object Detection | 2-3 FPS | 5-8 FPS |
| Face Recognition | 1-2 FPS | 3-5 FPS |
| Voice Commands | ✅ Works | ✅ Works |
| TTS Output | ✅ Works | ✅ Works |
| Dashboard | ✅ Works | ✅ Works |

---

## 🎯 Recommended Pi Configuration

For best experience on Raspberry Pi:

```json
{
  "perception": {
    "enable_emotion_detection": false,
    "enable_pose_tracking": false,
    "enable_gesture_recognition": false,
    "enable_face_recognition": true,
    "object_detection_interval": 5.0
  }
}
```

This disables heavy features and focuses on core functionality.

---

## Need Help?

Open an issue on GitHub: https://github.com/jay7-tech/memo/issues
