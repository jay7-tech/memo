# Auto-install script for Raspberry Pi 5 (64-bit Bookworm/Bullseye)
# Usage: bash install_pi.sh

echo "======================================"
echo "   MEMO Installation for RPi 5"
echo "======================================"

# 1. Update System
echo "[1/6] Updating system..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git python3-pip python3-venv cmake libopenblas-dev liblapack-dev libjpeg-dev

# 2. Install Audio Dependencies (PortAudio for PyAudio)
echo "[2/6] Installing Audio dependencies..."
sudo apt-get install -y portaudio19-dev python3-pyaudio flac

# 3. Create Virtual Environment (Recommended for Pi)
echo "[3/6] Setting up Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
fi
source venv/bin/activate

# 4. Install Core Python Libraries
echo "[4/6] Installing Python dependencies..."
pip install --upgrade pip

# INSTALL TORCH FIRST (ARM64 Optimized)
echo "Installing PyTorch (ARM64)..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# INSTALL OPENCV (Avoid wheel build issues by using headless or apt version if needed)
echo "Installing OpenCV..."
pip install opencv-python-headless  # Headless is often better/faster on Pi servers

# Install other requirements
pip install -r requirements_pi.txt

# 5. Fixes for Raspberry Pi specific issues
echo "[5/6] Applying Pi-specific fixes..."
# Uninstall heavy opencv-python if it got installed by dependencies
pip uninstall -y opencv-python
pip install opencv-python-headless

# 6. Setup complete
echo "======================================"
echo "   Installation Complete!"
echo "   To run MEMO:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo "======================================"
