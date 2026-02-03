# MEMO Replication Guide

This guide details how to set up the **MEMO** environment on a new machine (Raspberry Pi or PC) from scratch. It is based on a deep analysis of the codebase imports and system configuration scripts.

## 1. System Requirements

### Hardware
- **CPU**: Raspberry Pi 4/5 (ARM64) or PC (x86_64).
- **RAM**: Minimum 4GB (8GB recommended for AI models).
- **Camera**: USB Webcam or Raspberry Pi Camera Module.
- **Microphone**: USB Microphone or HAT.

### Operating System
- **Raspberry Pi**: Raspberry Pi OS (system 64-bit) *Bookworm* or *Bullseye*.
- **PC**: Windows 10/11 or Linux (Ubuntu 22.04+).

---

## 2. External Services (Mandatory)

MEMO relies on **Ollama** for its local intelligence. You must install this separately.

1.  **Install Ollama**:
    - **Linux/Pi**: `curl -fsSL https://ollama.com/install.sh | sh`
    - **Windows**: Download form [ollama.com](https://ollama.com).

2.  **Pull Required Models**:
    Run these commands in your terminal to download the brains:
    ```bash
    ollama pull phi3:mini       # Primary Brain (Fast, Capable)
    ollama pull tinyllama       # Fallback Brain (Very Fast)
    ```

3.  **Start Service**:
    Ensure Ollama is running (`ollama serve` or via system tray).

---

## 3. System Dependencies (Linux/Pi Only)

Before installing Python packages, you need these system libraries for Audio and Vision.

```bash
sudo apt update
sudo apt install -y \
    python3-opencv \
    python3-pyaudio portaudio19-dev \
    espeak espeak-ng libespeak-dev \
    alsa-utils \
    libatlas-base-dev \
    ffmpeg
```

*Note: On Windows, most of these are handled by pre-compiled wheels, but you may need to install [FFmpeg](https://ffmpeg.org/download.html) and add it to your PATH.*

---

## 4. Python Installation

MEMO requires **Python 3.10** or newer.

1.  **Clone & Enter Directory**:
    ```bash
    git clone <repo_url> memo
    cd memo
    ```

2.  **Create Virtual Environment** (Recommended):
    ```bash
    # Linux/Pi
    python3 -m venv venv --system-site-packages
    source venv/bin/activate

    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Verified Dependencies**:
    Use the verified requirements file generated from code analysis.
    ```bash
    pip install -r requirements_verified.txt
    ```

---

## 5. Configuration

1.  **Environment Variables**:
    Create a `.env` file for API keys (Optional, for Gemini Backup):
    ```ini
    GOOGLE_API_KEY=your_key_here
    ```

2.  **Hardware Config**:
    - **Pi**: The system automatically loads `config_rpi.json`.
    - **PC**: The system loads `config.json`.
    
    *Review these files to adjust `camera.source` (ID 0 or 1) if your camera isn't detected.*

---

## 6. Running the Application

### On Raspberry Pi (Recommended)
Use the included launcher script. It handles `libcamerify` (for fixing camera errors) and activates the environment automatically.

```bash
chmod +x run_memo.sh
./run_memo.sh
```

### On Windows / Manual Run
```bash
python main.py
```

### "Buzz" Command Note
If using the "buzz" (News) feature, ensure your machine has internet access, as it scrapes live tech news headers.

---

## Troubleshooting

- **Crash on Start (Permission/Audio)**: Ensure your user is in the `audio` and `video` groups:
  `sudo usermod -aG audio,video $USER`
- **Model Download Error**: Run `python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"` to verify model fetching.
