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

# Run optimized version if available
if [ -f "main_optimized.py" ]; then
    echo "Starting MEMO (Optimized)..."
    python main_optimized.py "$@"
else
    echo "Starting MEMO (Standard)..."
    python main.py "$@"
fi
