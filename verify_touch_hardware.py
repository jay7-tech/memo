import time
import sys
import os

print("=== MEMO Touch Sensor Diagnostic ===")

# 1. Check Library
try:
    from smbus2 import SMBus
    print("   ✓ smbus2 library found.")
except ImportError:
    print("   ❌ MISSING: smbus2. Run: pip install smbus2")
    sys.exit(1)

# 2. Touch Driver (Inline for standalone testing)
QT2120_ADDRESS = 0x1C
REG_CHIP_ID = 0x00
REG_KEY_STATUS_1 = 0x03

def check_i2c():
    """Scan simple I2C."""
    print("\n[Hardware] Scanning I2C Bus 1...")
    bus = SMBus(1)
    found = False
    try:
        # Try reading Chip ID
        chip_id = bus.read_byte_data(QT2120_ADDRESS, REG_CHIP_ID)
        print(f"   -> Read Address 0x{QT2120_ADDRESS:02X} => Chip ID: 0x{chip_id:02X}")
        if chip_id == 0x3E:
            print("   ✓ QT2120 Touch Sensor DETECTED!")
            found = True
        else:
            print(f"   ⚠️ Device found but ID mismatch (Expected 0x3E).")
    except Exception as e:
        print(f"   ❌ Failed to read 0x{QT2120_ADDRESS:02X}: {e}")
        print("      (Check SDA=Pin3, SCL=Pin5, VCC=3.3V, GND=Pin6)")
    
    bus.close()
    return found

def run_tap_test():
    """Run a loop to detect taps."""
    print("\n[Test] Running Tap Detection Loop (Ctrl+C to stop)...")
    print("       TRY TAPPING: 1, 2, or 3 times!")
    
    bus = SMBus(1)
    
    # Reset
    try:
        bus.write_byte_data(QT2120_ADDRESS, 0x07, 0x55) # Reset
        time.sleep(0.2)
        bus.write_byte_data(QT2120_ADDRESS, 0x06, 0x01) # Calibrate
        time.sleep(0.2)
    except:
        pass

    # Logic vars
    tap_count = 0
    in_transaction = False
    is_pressed = False
    last_tap_time = 0
    tap_gap_ms = 0.4 # 400ms
    
    try:
        while True:
            # Read Keys
            try:
                keys = bus.read_byte_data(QT2120_ADDRESS, REG_KEY_STATUS_1)
            except:
                keys = 0
                
            pressed = (keys > 0)
            now = time.time()
            
            # Edge Detection
            if pressed and not is_pressed:
                is_pressed = True
                tap_count += 1
                last_tap_time = now
                in_transaction = True
                print(f"   -> Raw Press! (Current Count: {tap_count})")
            
            elif not pressed and is_pressed:
                is_pressed = False
                
            # Timeout logic
            if in_transaction and (now - last_tap_time > tap_gap_ms):
                if not is_pressed:
                    print(f"   ✨ DETECTED GESTURE: {tap_count} TAP(s)!")
                    tap_count = 0
                    in_transaction = False
            
            if tap_count > 5: tap_count = 0
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nTest Stopped.")

if __name__ == "__main__":
    if check_i2c():
        run_tap_test()
    else:
        print("\n❌ Sensor not found. Cannot run tap test.")
