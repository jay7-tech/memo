# 🥧 MEMO - Raspberry Pi Setup Guide

This guide will help you deploy MEMO on a Raspberry Pi 5 (or 4).

## 1. System Preparation
Open a terminal on your Pi and run these commands to update the system and install system dependencies.

```bash
# Update System
sudo apt update && sudo apt upgrade -y

# Install Core Libraries (Audio, PortAudio, Espeak, Atlas)
sudo apt install -y python3-pyaudio portaudio19-dev
sudo apt install -y espeak libespeak1
sudo apt install -y libatlas-base-dev
sudo apt install -y python3-pip git
```

## 2. Setup Project
Clone your code (or copy the folder from your PC).

```bash
# Create folder
mkdir ~/MEMO
cd ~/MEMO

# (Copy your files here using USB or SFTP)
```

## 3. Create Virtual Environment
Avoid breaking system Python by using a virtual environment.

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate
```

## 4. Install Python Dependencies
Use the dedicated Pi requirements file.

```bash
# Upgrade pip first
pip install --upgrade pip

# Install dependencies
pip install -r requirements_pi.txt
```

> **Note:** Compiling some libraries (like numpy/scipy) on Pi Zero/3 might take a long time. Pi 4/5 should be relatively fast.

## 5. Setup Models

### Download Vosk Model (Offline Speech)
The speech engine needs the model file.

```bash
# Create models directory
mkdir -p models

# Download model (lightweight version)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

# Unzip
unzip vosk-model-small-en-us-0.15.zip -d models/

# Rename for auto-detection
mv models/vosk-model-small-en-us-0.15 models/vosk-model

# Cleanup
rm vosk-model-small-en-us-0.15.zip
```

## 7. Setup AI Brain (Ollama)
You mentioned `phi3:mini` is not on the Pi yet. You need to install Ollama and pull the model.

1. **Install Ollama** (if not installed):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull the Model**:
   This downloads the AI brain (~2GB).
   ```bash
   ollama pull phi3:mini
   ```

   *If `phi3:mini` is too slow on your Pi, try a smaller one:*
   ```bash
   ollama pull tinyllama
   ```

## 8. Run MEMO
Start the bot!

```bash
# Run with Pi specific config
python main.py
```

### Auto-Start on Boot (Optional)
To make MEMO run automatically when the Pi turns on:

1. Open crontab:
   ```bash
   crontab -e
   ```
2. Add this line at the bottom:
   ```bash
   @reboot /bin/bash /home/pi/MEMO/start_memo.sh
   ```
