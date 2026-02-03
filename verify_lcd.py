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
    
    print("LCD Started. Playing 'focus_on'...")
    lcd.play("focus_on", loop=True)
    time.sleep(2)
    
    print("Playing 'laugh'...")
    lcd.play("laugh", loop=False)
    time.sleep(2)
    
    print("Playing 'sleep'...")
    lcd.play("sleep", loop=True)
    time.sleep(2)
    
    print("Stopping...")
    lcd.stop()
    print("Done.")

if __name__ == "__main__":
    test()
