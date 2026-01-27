#!/bin/bash
# =============================================
# MEMO - Raspberry Pi 4 Installation Script
# =============================================
# Tested on: Raspberry Pi 4 (4GB), Pi OS 64-bit Bookworm
# 
# Usage: chmod +x install_rpi.sh && ./install_rpi.sh
# =============================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   MEMO Raspberry Pi 4 Installer        ║"
echo "║   Desktop AI Companion                 ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}📍 Installing in: $SCRIPT_DIR${NC}"
echo ""

# =============================================
# STEP 1: System Dependencies (via apt - FAST)
# =============================================
echo -e "${BLUE}[1/6] Installing system packages (pre-compiled)...${NC}"

sudo apt update

# OpenCV - Use system package (pre-compiled, 10 seconds vs 2+ hours)
sudo apt install -y python3-opencv

# Audio packages
sudo apt install -y python3-pyaudio portaudio19-dev
sudo apt install -y espeak espeak-ng libespeak-dev
sudo apt install -y alsa-utils

# Build essentials (minimal, for any pip packages that need compiling)
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y libatlas-base-dev  # For numpy

echo -e "${GREEN}✓ System packages installed${NC}"

# =============================================
# STEP 2: Create Virtual Environment
# =============================================
echo -e "${BLUE}[2/6] Setting up Python virtual environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages  # Include system packages!
    echo -e "${GREEN}✓ Created venv with system packages${NC}"
else
    echo -e "${YELLOW}→ Using existing venv${NC}"
fi

source venv/bin/activate
pip install --upgrade pip wheel

# =============================================
# STEP 3: Install PyTorch for ARM
# =============================================
echo -e "${BLUE}[3/6] Installing PyTorch for ARM...${NC}"

# Check if torch already installed
if python -c "import torch; print(torch.__version__)" 2>/dev/null; then
    echo -e "${GREEN}✓ PyTorch already installed${NC}"
else
    echo "Downloading PyTorch CPU wheels..."
    
    # Try official PyTorch CPU build
    if pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu 2>/dev/null; then
        echo -e "${GREEN}✓ PyTorch installed from pytorch.org${NC}"
    else
        echo -e "${YELLOW}→ Official wheels failed, trying piwheels...${NC}"
        
        if pip install torch torchvision 2>/dev/null; then
            echo -e "${GREEN}✓ PyTorch installed from piwheels${NC}"
        else
            echo -e "${YELLOW}⚠ PyTorch not available - face recognition disabled${NC}"
            echo "MEMO_LITE_MODE=1" > .env
        fi
    fi
fi

# =============================================
# STEP 4: Install Python packages
# =============================================
echo -e "${BLUE}[4/6] Installing Python packages...${NC}"

# Core packages (one by one for reliability)
PACKAGES=(
    "numpy>=1.24.0,<2.0.0"
    "psutil>=5.9.0"
    "pyttsx3>=2.90"
    "SpeechRecognition>=3.10.0"
    "flask>=3.0.0"
    "flask-socketio>=5.3.0"
    "python-socketio>=5.10.0"
    "Werkzeug>=3.0.0"
    "requests>=2.31.0"
    "colorlog>=6.8.0"
    "pyyaml>=6.0"
)

for pkg in "${PACKAGES[@]}"; do
    echo "Installing $pkg..."
    pip install "$pkg" --quiet || echo -e "${YELLOW}⚠ $pkg failed${NC}"
done

echo -e "${GREEN}✓ Core packages installed${NC}"

# =============================================
# STEP 5: Install Ultralytics (YOLOv8)
# =============================================
echo -e "${BLUE}[5/6] Installing YOLOv8...${NC}"

if pip install ultralytics --quiet 2>/dev/null; then
    echo -e "${GREEN}✓ Ultralytics (YOLOv8) installed${NC}"
else
    echo -e "${YELLOW}⚠ Ultralytics failed - object detection may not work${NC}"
fi

# Install Vosk for offline speech recognition
echo "Installing Vosk (offline speech)..."
pip install vosk>=0.3.45 --quiet || echo -e "${YELLOW}⚠ Vosk failed${NC}"

# =============================================
# STEP 6: Download Models
# =============================================
echo -e "${BLUE}[6/6] Downloading AI models...${NC}"

# Download YOLOv8 nano (smallest, fastest)
if [ ! -f "yolov8n.pt" ]; then
    echo "Downloading YOLOv8 nano model..."
    python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null || echo "Will download on first run"
fi

if [ ! -f "yolov8n-pose.pt" ]; then
    echo "Downloading YOLOv8 pose model..."
    python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')" 2>/dev/null || echo "Will download on first run"
fi

# Download Vosk model
if [ ! -d "models/vosk/vosk-model-en" ]; then
    echo "Downloading Vosk speech model (40MB)..."
    mkdir -p models/vosk
    cd models/vosk
    wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip || true
    if [ -f "vosk-model-small-en-us-0.15.zip" ]; then
        unzip -q vosk-model-small-en-us-0.15.zip
        mv vosk-model-small-en-us-0.15 vosk-model-en
        rm vosk-model-small-en-us-0.15.zip
        echo -e "${GREEN}✓ Vosk model downloaded${NC}"
    fi
    cd "$SCRIPT_DIR"
fi

# =============================================
# INSTALLATION COMPLETE
# =============================================
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════╗"
echo "║     ✓ Installation Complete!           ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}To run MEMO:${NC}"
echo "  ./run_memo.sh"
echo ""
echo -e "${BLUE}Or manually:${NC}"
echo "  source venv/bin/activate"
echo "  python main_optimized.py"
echo ""

# Check what's installed
echo -e "${BLUE}Installed Components:${NC}"
python -c "import cv2; print('  ✓ OpenCV:', cv2.__version__)" 2>/dev/null || echo "  ✗ OpenCV not found"
python -c "import torch; print('  ✓ PyTorch:', torch.__version__)" 2>/dev/null || echo "  ✗ PyTorch not found (lite mode)"
python -c "import ultralytics; print('  ✓ YOLOv8: installed')" 2>/dev/null || echo "  ✗ YOLOv8 not found"
python -c "import pyttsx3; print('  ✓ TTS: installed')" 2>/dev/null || echo "  ✗ TTS not found"
python -c "import vosk; print('  ✓ Vosk: installed')" 2>/dev/null || echo "  ✗ Vosk not found"
python -c "import flask; print('  ✓ Flask: installed')" 2>/dev/null || echo "  ✗ Flask not found"

echo ""
echo -e "${GREEN}🤖 MEMO is ready! Enjoy your AI companion!${NC}"
