import time
import os
import sys

# Mock cv2 if needed, but we assume it's installed
try:
    import cv2
except ImportError:
    print("CV2 missing")
    sys.exit(1)

# Paths
sys.path.append(os.getcwd())

print("Testing LCD Manager Integration...")

try:
    from interface.lcd import LCDManager
    print("Import successful.")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test():
    lcd = LCDManager()
    lcd.start()
    
    print("LCD Started. Testing States...")
    
    print("[1] Listening Mode (Wide Eyes)...")
    lcd.set_listening()
    time.sleep(3)
    
    print("[2] Thinking Mode (Searching)...")
    lcd.set_thinking()
    time.sleep(3)
    
    print("[3] Eureka! (Wink)...")
    lcd.trigger_eureka()
    time.sleep(2)
    
    print("[4] Selfie Flash!...")
    lcd.trigger_flash()
    time.sleep(2)
    
    print("Stopping...")
    lcd.stop()
    print("Done.")

if __name__ == "__main__":
    test()
