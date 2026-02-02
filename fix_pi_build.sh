#!/bin/bash
# Fix for "KeyError: '__version__'" and Pillow build errors on Pi

echo ">>> [1/4] Installing System Build Dependencies..."
sudo apt-get update
sudo apt-get install -y libjpeg-dev zlib1g-dev libpng-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff5-dev

echo ">>> [2/4] Downgrading setuptools (Fixes '__version__' error)..."
# Setuptools 70+ breaks some older wheel builds
pip install "setuptools<69" wheel

echo ">>> [3/4] Pre-installing Pillow..."
# Install Pillow explicitly to ensure it links to system libs
pip install "Pillow>=10.0.0" --no-cache-dir

echo ">>> [4/4] Installing FaceNet..."
pip install facenet-pytorch

echo ">>> DONE! Now try running main.py"
