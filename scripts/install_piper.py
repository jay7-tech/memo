
import os
import platform
import urllib.request
import tarfile
import shutil
import stat
import sys

def install_piper():
    print("=== Piper TTS Installer for Raspberry Pi ===")
    
    # 1. Detect OS/Arch
    arch = platform.machine().lower()
    system = platform.system().lower()
    print(f"System: {system}, Arch: {arch}")
    
    if system != "linux":
        print("Note: This script handles Linux/Pi installation. On Windows, Piper requires manual setup or WSL.")
        if input("Continue anyway? (y/n): ").lower() != 'y':
            return

    # 2. URLs
    # 2023.11.14-2 release
    PIPER_URL_ARM64 = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
    # high quality voice
    VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
    VOICE_JSON_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
    
    target_dir = os.path.join(os.getcwd(), "piper")
    os.makedirs(target_dir, exist_ok=True)
    models_dir = os.path.join(target_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # 3. Download Piper Binary
    piper_tar = os.path.join(target_dir, "piper.tar.gz")
    if not os.path.exists(os.path.join(target_dir, "piper")):
        print(f"Downloading Piper from {PIPER_URL_ARM64}...")
        try:
            urllib.request.urlretrieve(PIPER_URL_ARM64, piper_tar)
            print("Extracting...")
            with tarfile.open(piper_tar, "r:gz") as tar:
                tar.extractall(path=os.getcwd()) # Extracts into ./piper/
            
            # Cleanup
            os.remove(piper_tar)
            print("✓ Piper binary installed")
        except Exception as e:
            print(f"Error installing Piper: {e}")
            return
    else:
        print("✓ Piper binary already exists")
        
    # 4. Download Voice Model
    voice_path = os.path.join(models_dir, "en_US-lessac-medium.onnx")
    json_path = os.path.join(models_dir, "en_US-lessac-medium.onnx.json")
    
    if not os.path.exists(voice_path):
        print(f"Downloading Voice Model (Lessac Medium)...")
        try:
            urllib.request.urlretrieve(VOICE_URL, voice_path)
            urllib.request.urlretrieve(VOICE_JSON_URL, json_path)
            print("✓ Voice model installed")
        except Exception as e:
            print(f"Error downloading voice: {e}")
    else:
        print("✓ Voice model already exists")

    # 5. Test
    piper_bin = os.path.join(target_dir, "piper")
    if os.path.exists(piper_bin):
        # Make executable
        st = os.stat(piper_bin)
        os.chmod(piper_bin, st.st_mode | stat.S_IEXEC)
        print("\nInstallation Complete!")
        print(f"Binary: {piper_bin}")
        print(f"Model: {voice_path}")
        print("\nTo test:")
        print(f'echo "Hello world" | {piper_bin} --model {voice_path} --output_raw | aplay -r 22050 -f S16_LE -t raw -')
    else:
        print("Error: Piper binary not found after extraction.")

if __name__ == "__main__":
    install_piper()
