#!/bin/bash
# MEMO Startup Script
# Automatically handles Virtual Environment and Camera Compatibility

# 1. Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 2. Check for Libcamera (Pi 5 / Bullseye+)
if command -v libcamerify &> /dev/null; then
    echo ">> [System] Detected libcamerify. Enabling Pi Camera compatibility..."
    # Run with libcamerify wrapper to fix "Camera index out of range"
    libcamerify python main.py "$@"
else
    echo ">> [System] Standard startup..."
    python main.py "$@"
fi
