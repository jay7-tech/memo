"""
MEMO - Pi Full System Diagnostic
================================
Run this to verify all components are working INDEPENDENTLY before running main.py.
"""
import sys
import os
import time
import requests

def print_status(component, status, message=""):
    color = "\033[92m" if status == "OK" else "\033[91m"
    reset = "\033[0m"
    print(f"[{component:15}] {color}{status}{reset} {message}")

print("\n--- MEMO PI DIAGNOSTIC ---\n")

# 1. Check Libraries
try:
    import cv2
    import numpy
    print_status("OpenCV", "OK", cv2.__version__)
except ImportError:
    print_status("OpenCV", "FAIL", "Not installed")

try:
    import ultralytics
    print_status("YOLO", "OK", ultralytics.__version__)
except ImportError:
    print_status("YOLO", "FAIL", "pip install ultralytics")

try:
    from facenet_pytorch import InceptionResnetV1
    print_status("FaceNet", "OK", "Library found")
except ImportError:
    print_status("FaceNet", "FAIL", "pip install facenet-pytorch")

# 2. Check Camera
try:
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print_status("Camera", "OK", f"Resolution: {frame.shape}")
        else:
            print_status("Camera", "FAIL", "Opened but no frame")
        cap.release()
    else:
        print_status("Camera", "FAIL", "Could not open /dev/video0")
except Exception as e:
    print_status("Camera", "FAIL", str(e))

# 3. Check Ollama (Phi3)
print("\n[AI] Testing Ollama connection (may take 10s)...")
try:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "phi3:mini", 
        "prompt": "Hello", 
        "stream": False,
        "options": {"num_ctx": 1024}
    }
    start = time.time()
    res = requests.post(url, json=payload, timeout=30)
    if res.status_code == 200:
        elapsed = time.time() - start
        print_status("Ollama", "OK", f"Replied in {elapsed:.1f}s: {res.json().get('response', '')[:20]}...")
    else:
        print_status("Ollama", "FAIL", f"Status {res.status_code}")
except Exception as e:
    print_status("Ollama", "FAIL", f"Is 'ollama serve' running? {e}")

# 4. Check Config
import json
try:
    with open('config_rpi.json', 'r') as f:
        cfg = json.load(f)
        model = cfg.get('llm', {}).get('model')
        burst = cfg.get('perception', {}).get('burst_mode')
        face_thresh = cfg.get('perception', {}).get('face_threshold')
        print_status("Config", "OK", f"Model: {model}, Burst: {burst}, FaceThresh: {face_thresh}")
except Exception as e:
    print_status("Config", "FAIL", f"JSON Error: {e}")

print("\n--- END DIAGNOSTIC ---")
