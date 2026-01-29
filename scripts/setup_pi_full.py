
import subprocess
import os
import sys
import platform

def run_cmd(cmd, ignore_error=False):
    print(f"\n[EXEC] {cmd}")
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if not ignore_error:
            # Don't exit, just warn, as some things might be partially installed
            print("Warning: Step failed. Continuing...")

def check_command(cmd):
    return subprocess.call(f"which {cmd}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def setup():
    print("====================================")
    print("    MEMO - RASPBERRY PI REPAIR      ")
    print("====================================")
    
    if platform.system().lower() != "linux":
        print("WARNING: This script is intended for Linux/Raspberry Pi.")
        if input("Continue anyway? (y/n): ").lower() != 'y':
            return

    # 1. System Dependencies
    print("\n[1/5] Installing System Libraries...")
    print("This requires sudo. You may be asked for your password.")
    
    deps = [
        "libopenblas-dev",
        "liblapack-dev", 
        "libatlas-base-dev",  # For numpy/torch optimization
        "libportaudio2",      # For PyAudio (Microphone)
        "libasound-dev",      # For Audio
        "espeak",             # For fallback TTS
        "python3-pyaudio"     # System package for PyAudio is often more reliable on Pi
    ]
    run_cmd(f"sudo apt-get update && sudo apt-get install -y {' '.join(deps)}")

    # 2. Python Dependencies
    print("\n[2/5] Installing Python Libraries...")
    
    # Install PyTorch (CPU version) - Critical for Face Recognition
    # Using default pip install for aarch64 usually grabs the right wheel now
    run_cmd(f"{sys.executable} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
    
    # Install other missing core libs
    libs = [
        "facenet-pytorch",   # Face Rec
        "ultralytics",       # YOLO/Pose
        "SpeechRecognition", # Voice Input
        "requests",
        "flask",
        "flask-socketio",
        "colorlog",
        "psutil"
    ]
    run_cmd(f"{sys.executable} -m pip install {' '.join(libs)}")

    # 3. AI (Ollama)
    print("\n[3/5] Checking AI (Ollama)...")
    if not check_command("ollama"):
        print("Installing Ollama...")
        run_cmd("curl -fsSL https://ollama.com/install.sh | sh")
    else:
        print("✓ Ollama is installed")

    print("Pulling AI Model (phi:latest)...")
    # Try requesting the model. If daemon not running, this might fail.
    try:
        run_cmd("ollama pull phi:latest")
    except:
        print("Could not pull model. Is Ollama running?")
        print("Try running: 'ollama serve' in a separate terminal.")

    # 4. Piper TTS (High Quality Voice)
    print("\n[4/5] Setting up Piper TTS...")
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    piper_script = os.path.join(scripts_dir, "install_piper.py")
    
    if os.path.exists(piper_script):
        run_cmd(f"{sys.executable} {piper_script}")
    else:
        print(f"Warning: {piper_script} not found. Skipping Piper setup.")

    # 5. Microphone Diagnostics
    print("\n[5/5] Diagnostic Checks...")
    
    # Audio Check
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        cnt = p.get_device_count()
        print(f"✓ Audio System Detected: {cnt} devices found")
        p.terminate()
    except Exception as e:
        print(f"❌ Audio System Issue: {e}")
        print("Try: sudo apt-get install python3-pyaudio")

    print("\n====================================")
    print("           REPAIR COMPLETE          ")
    print("====================================")
    print("Recommended Next Steps:")
    print("1. Reboot your Pi: sudo reboot")
    print("2. Make sure Ollama is running: ollama serve")
    print("3. Run MEMO: python main.py")

if __name__ == "__main__":
    setup()
