#!/bin/bash

# Configuration
CONFIG_TXT="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_TXT" ]; then
    CONFIG_TXT="/boot/config.txt"
fi

echo "=== Dual Touch Sensor Setup ==="
echo "Target Config: $CONFIG_TXT"

# 1. Install Tools
echo "[1] Installing I2C priorities..."
sudo apt-get update
sudo apt-get install -y i2c-tools python3-smbus

# 2. Check for Overlay
OVERLAY="dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=27,i2c_gpio_scl=22"

if grep -q "i2c-gpio,bus=3" "$CONFIG_TXT"; then
    echo "[2] Bus 3 Overlay already exists. Skipping."
else
    echo "[2] Adding Bus 3 Overlay (Pins 27, 22)..."
    # Backup
    sudo cp "$CONFIG_TXT" "${CONFIG_TXT}.bak"
    # Append
    echo "" | sudo tee -a "$CONFIG_TXT"
    echo "# MEMO: Software I2C for Second Touch Sensor" | sudo tee -a "$CONFIG_TXT"
    echo "$OVERLAY" | sudo tee -a "$CONFIG_TXT"
    echo "    ✓ Added to config."
fi

# 3. Permissions
echo "[3] Setting permissions..."
sudo usermod -aG i2c $USER

echo ""
echo "=== SETUP COMPLETE ==="
echo "⚠️  You MUST REBOOT your Pi for the new bus to appear!"
echo "    Run: sudo reboot"
