#!/bin/bash
# =============================================
# MEMO - Raspberry Pi Auto Installer
# =============================================
# Usage: chmod +x install_rpi.sh && ./install_rpi.sh
# =============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════╗"
echo "║     MEMO - Raspberry Pi Auto Installer     ║"
echo "║        Desktop Companion Bot Setup         ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null && ! grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}⚠ Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}📍 Installing in: $SCRIPT_DIR${NC}"
echo ""

# =============================================
# Step 1: Update System
# =============================================
echo -e "${BLUE}[1/8] Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

# =============================================
# Step 2: Install System Dependencies
# =============================================
echo -e "${BLUE}[2/8] Installing system dependencies...${NC}"

# Build tools
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y cmake build-essential pkg-config
sudo apt install -y libatlas-base-dev libopenblas-dev

# Audio dependencies
sudo apt install -y portaudio19-dev python3-pyaudio
sudo apt install -y espeak espeak-ng libespeak-dev
sudo apt install -y alsa-utils pulseaudio

# Camera support
sudo apt install -y libcamera-dev libcap-dev

# Other utilities
sudo apt install -y git wget unzip

echo -e "${GREEN}✓ System dependencies installed${NC}"

# =============================================
# Step 3: Create Virtual Environment
# =============================================
echo -e "${BLUE}[3/8] Setting up Python virtual environment...${NC}"

if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment exists, activating...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Created virtual environment${NC}"
fi

source venv/bin/activate
pip install --upgrade pip wheel setuptools

# =============================================
# Step 4: Install PyTorch for ARM
# =============================================
echo -e "${BLUE}[4/8] Installing PyTorch for Raspberry Pi...${NC}"

# Try PyTorch CPU-only build first
echo "Attempting PyTorch CPU installation..."
if pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu 2>/dev/null; then
    echo -e "${GREEN}✓ PyTorch installed from pytorch.org${NC}"
else
    echo -e "${YELLOW}PyTorch from pytorch.org failed, trying piwheels...${NC}"
    if pip install torch torchvision --index-url https://www.piwheels.org/simple 2>/dev/null; then
        echo -e "${GREEN}✓ PyTorch installed from piwheels${NC}"
    else
        echo -e "${YELLOW}⚠ PyTorch installation failed. Running in lite mode.${NC}"
        echo "MEMO_LITE_MODE=1" >> .env
        LITE_MODE=true
    fi
fi

# =============================================
# Step 5: Install OpenCV
# =============================================
echo -e "${BLUE}[5/8] Installing OpenCV...${NC}"

pip install opencv-python-headless>=4.8.0 || {
    echo -e "${YELLOW}pip install failed, using system OpenCV...${NC}"
    sudo apt install -y python3-opencv
}

echo -e "${GREEN}✓ OpenCV installed${NC}"

# =============================================
# Step 6: Install Python Dependencies
# =============================================
echo -e "${BLUE}[6/8] Installing Python packages...${NC}"

# Install packages one by one to handle failures gracefully
PACKAGES=(
    "numpy>=1.24.0"
    "pyttsx3"
    "SpeechRecognition"
    "vosk>=0.3.45"
    "flask"
    "flask-socketio>=5.3.0"
    "python-socketio>=5.10.0"
    "requests"
    "werkzeug"
    "colorlog>=6.8.0"
    "pyyaml>=6.0"
    "psutil>=5.9.0"
)

for pkg in "${PACKAGES[@]}"; do
    echo "Installing $pkg..."
    pip install "$pkg" || echo -e "${YELLOW}⚠ Failed to install $pkg, continuing...${NC}"
done

# Try optional packages
echo "Installing optional packages..."
pip install ultralytics 2>/dev/null || echo -e "${YELLOW}⚠ Ultralytics skipped (optional)${NC}"
pip install facenet-pytorch 2>/dev/null || echo -e "${YELLOW}⚠ facenet-pytorch skipped (optional)${NC}"
pip install mediapipe 2>/dev/null || echo -e "${YELLOW}⚠ MediaPipe skipped (optional)${NC}"
pip install openwakeword 2>/dev/null || echo -e "${YELLOW}⚠ OpenWakeWord skipped (optional)${NC}"

echo -e "${GREEN}✓ Python packages installed${NC}"

# =============================================
# Step 7: Download Vosk Model
# =============================================
echo -e "${BLUE}[7/8] Downloading Vosk speech model...${NC}"

mkdir -p models/vosk
cd models/vosk

if [ ! -d "vosk-model-en" ]; then
    echo "Downloading Vosk model (40MB)..."
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip -q vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 vosk-model-en
    rm vosk-model-small-en-us-0.15.zip
    echo -e "${GREEN}✓ Vosk model downloaded${NC}"
else
    echo -e "${GREEN}✓ Vosk model already exists${NC}"
fi

cd "$SCRIPT_DIR"

# =============================================
# Step 8: Create Pi-optimized config
# =============================================
echo -e "${BLUE}[8/8] Creating optimized configuration...${NC}"

# Backup existing config if exists
if [ -f "config.json" ]; then
    cp config.json config.json.backup
fi

# Create Pi-optimized config
cat > config_rpi.json << 'EOF'
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
    "enable_gesture_recognition": false,
    "enable_face_recognition": true,
    "object_detection_interval": 5.0,
    "face_recognition_interval": 2.0
  },
  "voice": {
    "enable_voice_input": true,
    "wake_word": "hey memo",
    "wake_word_threshold": 0.5,
    "speech_timeout": 5.0,
    "use_vosk": true
  },
  "dashboard": {
    "enable_dashboard": true,
    "dashboard_port": 5000,
    "host": "0.0.0.0"
  },
  "llm": {
    "enable_llm": true,
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.7
  }
}
EOF

echo -e "${GREEN}✓ Created config_rpi.json${NC}"

# =============================================
# Create run script
# =============================================
cat > run_memo.sh << 'EOF'
#!/bin/bash
# Quick run script for MEMO

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Use Pi-optimized config if running on Pi
if [ -f "config_rpi.json" ]; then
    export MEMO_CONFIG="config_rpi.json"
fi

# Run MEMO
python main.py
EOF

chmod +x run_memo.sh

# =============================================
# Installation Complete
# =============================================
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════╗"
echo "║     ✓ MEMO Installation Complete!          ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}To run MEMO:${NC}"
echo "  cd $SCRIPT_DIR"
echo "  ./run_memo.sh"
echo ""
echo -e "${BLUE}Or manually:${NC}"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""

if [ "$LITE_MODE" = true ]; then
    echo -e "${YELLOW}⚠ Running in LITE MODE (PyTorch unavailable)${NC}"
    echo "  Face recognition will be disabled."
    echo ""
fi

echo -e "${GREEN}Enjoy MEMO on your Raspberry Pi! 🤖${NC}"
