
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
        "libatlas-base-dev",
        "libportaudio2",
        "portaudio19-dev",    # CRITICAL: Needed to compile PyAudio in venv
        "libasound-dev",
        "espeak",
        # Image library dependencies for Pillow build
        "libjpeg-dev",
        "zlib1g-dev", 
        "libfreetype6-dev", 
        "liblcms2-dev", 
        "libopenjp2-7-dev", 
        "libtiff-dev"
    ]
    run_cmd(f"sudo apt-get update && sudo apt-get install -y {' '.join(deps)}")

    # 2. Python Dependencies
    print("\n[2/5] Installing Python Libraries...")
    
    # 2a. Install PyTorch
    run_cmd(f"{sys.executable} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")

    # 2b. Install Pillow explicitly (Latest version often fixes build issues on new Python)
    print("Installing Pillow...")
    run_cmd(f"{sys.executable} -m pip install --upgrade Pillow")

    # 2c. Install PyAudio explicitly (Needs portaudio19-dev from above)
    print("Installing PyAudio (Voice Engine)...")
    run_cmd(f"{sys.executable} -m pip install pyaudio")
    
    # 2d. Install facenet-pytorch NO DEPS (to avoid Pillow version conflict)
    print("Installing FaceNet & Utilities...")
    run_cmd(f"{sys.executable} -m pip install facenet-pytorch --no-deps")
    
    # 2e. Install other libs
    libs = [
        "ultralytics",
        "SpeechRecognition", 
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

    print("Pulling AI Models...")
    # Pull tinyllama for speed, phi for quality if needed
    # Try requesting the model. If daemon not running, this might fail.
    try:
        run_cmd("ollama pull tinyllama:latest")
        run_cmd("ollama pull phi:latest")
    except:
        print("Could not pull models. Is Ollama running?")
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
    print("\n[5/5] Setup Complete!")
    print("\nIMPORTANT: Please run these commands if you still have issues:")
    print("  1. Test Audio:  paplay /usr/sounds/alsa/Front_Center.wav")
    print("  2. Test AI:     ollama run phi:latest 'hello'")
    
    print("\nTo start MEMO:")
    print(f"  {sys.executable} main.py")
    print("Make sure Ollama is running: ollama serve")

if __name__ == "__main__":
    setup()
