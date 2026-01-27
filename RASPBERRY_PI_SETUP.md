# 🍓 MEMO - Raspberry Pi 4 Setup Guide

Complete step-by-step instructions to install and run MEMO on Raspberry Pi 4.

---

## 📋 Prerequisites

- **Hardware**: Raspberry Pi 4 (4GB RAM recommended)
- **OS**: Raspberry Pi OS 64-bit (Bookworm)
- **Storage**: 8GB+ free space
- **Camera**: USB webcam or Pi Camera
- **Audio**: USB microphone + speakers/headphones

---

## 🚀 STEP-BY-STEP INSTALLATION

### Step 1: Update Your Pi

```bash
sudo apt update && sudo apt upgrade -y
```

---

### Step 2: Install System Dependencies

```bash
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y python3-opencv python3-pyaudio
sudo apt install -y portaudio19-dev espeak espeak-ng libespeak-dev
sudo apt install -y libatlas-base-dev alsa-utils git wget unzip
```

---

### Step 3: Clone MEMO from GitHub

```bash
cd ~
git clone https://github.com/jay7-tech/memo.git
cd memo
```

---

### Step 4: Create Virtual Environment

```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install --upgrade pip wheel
```

---

### Step 5: Install PyTorch for ARM

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

**If that fails, try:**
```bash
pip install torch torchvision
```

---

### Step 6: Install Python Packages

```bash
pip install numpy>=1.24.0 psutil>=5.9.0
pip install pyttsx3 SpeechRecognition
pip install flask flask-socketio python-socketio Werkzeug requests
pip install colorlog pyyaml
pip install ultralytics
pip install vosk>=0.3.45
```

---

### Step 7: Download Vosk Speech Model

```bash
mkdir -p models/vosk
cd models/vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-en
rm vosk-model-small-en-us-0.15.zip
cd ~/memo
```

---

### Step 8: Test the Installation

```bash
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import ultralytics; print('YOLOv8: OK')"
python -c "import pyttsx3; print('TTS: OK')"
```

---

### Step 9: Run MEMO

```bash
# Make sure you're in the memo folder with venv active
cd ~/memo
source venv/bin/activate

# Run the optimized version
python main_optimized.py
```

---

## 🎯 QUICK START (ONE-LINER)

If you want to do everything at once, run:

```bash
cd ~ && git clone https://github.com/jay7-tech/memo.git && cd memo && chmod +x install_rpi.sh && ./install_rpi.sh
```

---

## 📺 After Installation - Running MEMO

### Option 1: Using the launcher script
```bash
cd ~/memo
./run_memo.sh
```

### Option 2: Manual run
```bash
cd ~/memo
source venv/bin/activate
python main_optimized.py
```

### Option 3: With a specific camera
```bash
# USB camera (usually device 0)
python main_optimized.py 0

# If you have multiple cameras, try 1
python main_optimized.py 1
```

---

## 🖥️ Access the Dashboard

Once MEMO is running, open a browser on any device on your network:

```
http://<raspberry-pi-ip>:5000
```

To find your Pi's IP:
```bash
hostname -I
```

---

## ⌨️ MEMO Controls

### Keyboard Shortcuts (in the camera window):
| Key | Action |
|-----|--------|
| `q` | Quit MEMO |
| `f` | Toggle Focus Mode |
| `s` | Take Selfie |
| `v` | Toggle Voice Input |

### Console Commands:
| Command | Action |
|---------|--------|
| `focus on` | Enable distraction detection |
| `focus off` | Disable distraction detection |
| `register <name>` | Register your face |
| `where is <object>` | Find object location |
| `voice on` | Enable voice commands |
| `voice off` | Disable voice commands |
| `quit` | Exit MEMO |

---

## 🔧 Troubleshooting

### Camera not working?
```bash
# Check if camera is detected
ls /dev/video*

# Test camera
libcamera-hello --list-cameras

# If using USB webcam, try:
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"
```

### No audio output?
```bash
# Test speakers
espeak "Hello, testing audio"

# Check audio devices
aplay -l
```

### PyTorch installation failed?
```bash
# Run without face recognition (lite mode)
export MEMO_LITE_MODE=1
python main_optimized.py
```

### High CPU usage?
Edit `config_rpi.json` and increase frame_skip:
```json
{
  "perception": {
    "frame_skip": 8
  }
}
```

---

## 🔄 Auto-Start on Boot (Optional)

To make MEMO start when your Pi boots:

```bash
# Create a service file
sudo nano /etc/systemd/system/memo.service
```

Paste this:
```ini
[Unit]
Description=MEMO Desktop Companion
After=network.target

[Service]
ExecStart=/home/pi/memo/run_memo.sh
WorkingDirectory=/home/pi/memo
User=pi
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable memo
sudo systemctl start memo
```

---

## 📊 Expected Performance on Pi 4

| Feature | Performance |
|---------|-------------|
| Object Detection | 2-5 FPS |
| Pose Tracking | 2-5 FPS |
| Voice Commands | Real-time |
| TTS Output | Real-time |
| Dashboard | Smooth |

---

## ✅ All Commands in Order (Copy-Paste Ready)

```bash
# ======== FULL INSTALLATION ========

# Step 1: Update
sudo apt update && sudo apt upgrade -y

# Step 2: System packages
sudo apt install -y python3-pip python3-venv python3-dev python3-opencv python3-pyaudio portaudio19-dev espeak espeak-ng libespeak-dev libatlas-base-dev alsa-utils git wget unzip

# Step 3: Clone
cd ~
git clone https://github.com/jay7-tech/memo.git
cd memo

# Step 4: Virtual environment
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install --upgrade pip wheel

# Step 5: PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Step 6: Python packages
pip install numpy psutil pyttsx3 SpeechRecognition flask flask-socketio python-socketio Werkzeug requests colorlog pyyaml ultralytics vosk

# Step 7: Vosk model
mkdir -p models/vosk && cd models/vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-en
rm vosk-model-small-en-us-0.15.zip
cd ~/memo

# Step 8: Run!
python main_optimized.py
```

---

## 🎉 You're Done!

MEMO should now be running on your Raspberry Pi 4!

**Dashboard**: `http://<your-pi-ip>:5000`

Enjoy your AI desktop companion! 🤖
