#!/bin/bash
# MEMO Launcher for Linux/Raspberry Pi

echo "===================================="
echo "      MEMO - Desktop Companion      "
echo "===================================="
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Use Pi config if on Raspberry Pi
if grep -q "Raspberry Pi\|BCM" /proc/cpuinfo 2>/dev/null; then
    echo "Detected Raspberry Pi - using optimized config"
    export MEMO_CONFIG="config_rpi.json"
fi

echo "Starting MEMO..."
# Check for libcamerify (Fix for /dev/video0 error on Bookworm)
if command -v libcamerify &> /dev/null; then
    echo "Running with libcamerify wrapper..."
    libcamerify python main.py "$@"
else
    python main.py "$@"
fi
