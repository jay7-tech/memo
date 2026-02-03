import os
import requests
from pathlib import Path

MODEL_DIR = Path("perception/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "face_detection_yunet_2023mar.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    # Using a reliable resonant/mobilefacenet ONNX or similar. 
    # w600k_r50 is standard ArcFace. 
    # For now, let's use a known MobileFaceNet ONNX for speed.
    "mobilefacenet.onnx": "https://github.com/biubug6/Pytorch_Retinaface/raw/master/weights/mobile0.25_Final.pth" # Wait, need ONNX.
}

# Reliable sources for ready-to-use ONNX models are tricky without conversion scripts.
# Let's use a specific GDrive link or a known GitHub release for MobileFaceNet ONNX.
# InsightFace provides them but often heavily wrapped.
# Alternative: version-RFB-320.onnx for detection, but YuNet is better.

# Let's use the OpenCV Zoo YuNet (Confirmed good).
# For Recognition, we can use the specific ONNX export of MobileFaceNet.
# Source: https://github.com/DaJiu/MobileFaceNet-ONNX (example)

# Updating URLs to direct raw content
MODELS = {
    "face_detection_yunet_2023mar.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
}
# SFace is OpenCV's recommended recognizer. Small, fast, accurate. perfect for Pi.

def download_file(url, filename):
    local_path = MODEL_DIR / filename
    if local_path.exists():
        print(f"✓ {filename} already exists.")
        return

    print(f"⬇️ Downloading {filename}...")
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✓ Downloaded {filename}")
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")

if __name__ == "__main__":
    print(f"Downloading models to {MODEL_DIR}...")
    for name, url in MODELS.items():
        download_file(url, name)
    print("Done.")
