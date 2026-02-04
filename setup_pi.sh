#!/bin/bash
# One-Click Setup for MEMO on Raspberry Pi 5
# Run as: ./setup_pi.sh

echo "======================================="
echo "   MEMO - Raspberry Pi Setup Helper    "
echo "======================================="

# 1. Enable SPI Interface (Hardware Requirement)
echo "[1/4] Checking Hardware Config (SPI)..."
if grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "   ✓ SPI is already enabled."
else
    echo "   + Enabling SPI interface..."
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt > /dev/null
    echo "   ⚠️ SPI Enabled."
    NEED_REBOOT=true
fi

# 1.5 Enable I2C Interface (Touch Sensor)
echo "[1/4b] Checking Hardware Config (I2C)..."
if grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "   ✓ I2C is already enabled."
else
    echo "   + Enabling I2C interface..."
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
    # Also load module now if possible
    sudo modprobe i2c-dev
    echo "   ⚠️ I2C Enabled. REBOOT required."
    NEED_REBOOT=true
fi

# 2. Install Dependencies
echo "[2/4] Installing Drivers & Libraries..."
# System level for GPIO/SPI access
sudo apt update -qq
sudo apt install -y python3-lgpio python3-spidev libatlas-base-dev libopenblas-dev -qq

# Python level
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "   - Installing python requirements (this may take a minute)..."
    pip install -r requirements_verified.txt > /dev/null
    echo "   ✓ Python dependencies installed."
else
    echo "   ❌ No 'venv' found. Please run this inside your project folder."
    exit 1
fi

# 3. Download AI Models
echo "[3/4] Downloading AI Models..."
python scripts/download_face_models.py

# 4. Generate Visual Assets
echo "[4/4] Generating LCD Graphics..."
python scripts/generate_ultimate_assets.py
python scripts/generate_aesthetic_selfie.py
python scripts/generate_focus_final.py

echo "======================================="
echo "          SETUP COMPLETE! 🚀           "
echo "======================================="

if [ "$NEED_REBOOT" = true ]; then
    echo "⚠️  IMPORTANT: You must REBOOT your Pi to enable the screen."
    echo "    Type: sudo reboot"
else
    echo "You are ready to go!"
    echo "Run: ./run_memo.sh"
fi
