#!/bin/bash
# MEMO Launcher for Raspberry Pi (Bookworm/Bullseye compatible)

echo "[MEMO] Starting..."
echo "[MEMO] Activating virtual environment..."
source venv/bin/activate

# Check if libcamerify exists (needed for Bookworm OS to us OpenCV)
if command -v libcamerify &> /dev/null; then
    echo "[MEMO] Detected libcamera system. Using libcamerify wrapper."
    libcamerify python main.py
else
    echo "[MEMO] Legacy camera system detected. Standard launch."
    python main.py
fi
