import cv2
import os
import glob

print("=== MEMO CAMERA DIAGNOSTIC ===")

# 1. List /dev/video* devices
devices = glob.glob('/dev/video*')
print(f"Found devices: {devices}")
if not devices:
    print("❌ No /dev/video devices found! Is the camera connected?")

# 2. Try OpenCV indices
print("\nTesting OpenCV Indices...")
for idx in range(10):
    print(f"Testing Index {idx}...", end=" ", flush=True)
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✓ WORKING! Resolution: {frame.shape[1]}x{frame.shape[0]}")
            cap.release()
        else:
            print(f"Opened but failed to read frame.")
    else:
        print("Failed to open.")
        
print("\n=== DIAGNOSTIC COMPLETE ===")
