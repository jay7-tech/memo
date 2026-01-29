
import sys
import os
import subprocess
import time

print("=== MEMO PI DIAGNOSTIC TOOL ===")
print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")

print("\n--- 1. CHECKING LIBRARIES ---")

# Check Torch
try:
    import torch
    print(f"✓ Torch installed: {torch.__version__}")
except ImportError as e:
    print(f"❌ Torch MISSING: {e}")

# Check FaceNet
try:
    from facenet_pytorch import MTCNN, InceptionResnetV1
    print("✓ Facenet-PyTorch installed")
except ImportError as e:
    print(f"❌ Facenet-PyTorch MISSING: {e}")
    # specific check for Pillow
    try:
        import PIL
        print(f"  (Pillow is installed: {PIL.__version__})")
    except:
        print("  (Pillow is ALSO missing)")

# Check PyAudio
try:
    import pyaudio
    print("✓ PyAudio installed")
except ImportError as e:
    print(f"❌ PyAudio MISSING: {e}")

# Check Piper
piper_path = "./piper/piper"
if os.path.exists(piper_path):
    print("✓ Piper binary found")
else:
    print("❌ Piper binary NOT found at ./piper/piper")


print("\n--- 2. CHECKING AUDIO DEVICES ---")
try:
    import pyaudio
    p = pyaudio.PyAudio()
    count = p.get_device_count()
    print(f"Found {count} audio devices:")
    for i in range(count):
        info = p.get_device_info_by_index(i)
        print(f"  [{i}] {info['name']} (In: {info['maxInputChannels']}, Out: {info['maxOutputChannels']})")
    p.terminate()
except Exception as e:
    print(f"Could not list devices: {e}")

print("\n--- 3. TESTING AUDIO OUTPUT ---")
print("Attempting to play test sound via 'aplay'...")
try:
    # Try generating a simple beep with aplay directly if possible, or just checking version
    res = subprocess.run(["aplay", "--version"], capture_output=True, text=True)
    print(f"aplay version: {res.stdout.strip()}")
    
    # Check volume
    print("Checking Mixer levels (amixer):")
    subprocess.run(["amixer", "sget", "Master"], capture_output=False)
except Exception as e:
    print(f"aplay check failed: {e}")

print("\n--- DIAGNOSTIC COMPLETE ---")
print("Please copy the output above and share it.")
