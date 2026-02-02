import cv2
import os
import glob

print("--- Camera Diagnostic ---")

# 1. Check /dev/video* devices
devices = glob.glob("/dev/video*")
print(f"System Video Devices: {devices}")

if not devices:
    print("[ERROR] No /dev/video* devices found!")
    print("Suggestions:")
    print("1. Check ribbon cable connection.")
    print("2. Run 'libcamera-hello' to verify hardware.")
    print("3. Ensure 'dtoverlay=imx219' (or your sensor) is in /boot/firmware/config.txt")
else:
    print("Devices found. Testing OpenCV access...")

# 2. Test Indices
for idx in range(5):
    print(f"\nTesting Index {idx}...")
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"[SUCCESS] Index {idx} is working! Resolution: {frame.shape}")
            cap.release()
        else:
            print(f"[FAIL] Index {idx} opened but returned no frame.")
    else:
        print(f"[FAIL] Index {idx} could not be opened.")
        
print("\n--- End Diagnostic ---")
