import sys
import os
import time

print("=== MEMO LCD Hardware Diagnostic ===")
print(f"Python: {sys.version}")

# 1. Check Libraries
print("\n[1/5] Checking Libraries...")
try:
    import spidev
    print("   ✓ spidev found")
except ImportError:
    print("   ❌ MISSING: spidev")

try:
    import lgpio
    print("   ✓ lgpio found")
except ImportError:
    print("   ❌ MISSING: lgpio (required for Pi 5)")

try:
    import RPi.GPIO
    print("   ✓ RPi.GPIO found (Legacy)")
except ImportError:
    print("   - RPi.GPIO not found (Normal for Pi 5)")

try:
    from PIL import Image
    print("   ✓ PIL found")
except ImportError:
    print("   ❌ MISSING: Pillow")

# 2. Check SPI Device
print("\n[2/5] Checking SPI Device...")
if os.path.exists("/dev/spidev0.0"):
    print("   ✓ /dev/spidev0.0 exists")
else:
    print("   ❌ MISSING: /dev/spidev0.0")
    print("      -> Run 'sudo raspi-config', Interface -> SPI -> Yes")
    print("      -> Then REBOOT.")

if os.path.exists("/dev/spidev0.1"):
    print("   - /dev/spidev0.1 exists")

# 3. Check GPIO Chip
print("\n[3/5] Checking GPIO Chip...")
try:
    h = lgpio.gpiochip_open(0)
    print("   ✓ Opened gpiochip_0")
    
    # Try generic pin claim (Pin 25 = DC)
    try:
        lgpio.gpio_claim_output(h, 25, 0)
        print("   ✓ Claimed GPIO 25 (DC)")
        lgpio.gpio_free(h, 25)
    except Exception as e:
        print(f"   ❌ Failed to claim GPIO 25: {e}")
        
    lgpio.gpiochip_close(h)
except Exception as e:
    print(f"   ❌ GPIO Error: {e}")

# 4. Attempt Driver Init
print("\n[4/5] Attempting Driver Initialization...")
try:
    # Set path to allow import
    sys.path.append(os.getcwd())
    from interface.lcd.driver import LCD_ST7735
    
    print("   -> Initializing LCD_ST7735...")
    lcd = LCD_ST7735()
    print("   ✓ Driver Initialized Successfully!")
    
    # 5. Draw Image
    print("\n[5/5] Drawing Test Pattern...")
    img = Image.new('RGB', (128, 128), (0, 255, 255)) # Cyan
    lcd.display_image(img)
    print("   ✓ Sent Cyan Screen.")
    time.sleep(1)
    
    img = Image.new('RGB', (128, 128), (255, 0, 255)) # Magenta
    lcd.display_image(img)
    print("   ✓ Sent Magenta Screen.")
    
    lcd.close()

except Exception as e:
    print(f"\n❌ DRIVER FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Diagnostic Complete ===")
