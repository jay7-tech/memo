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
    print("\n[Hardware] Scanning I2C Bus 1 for ANY devices...")
    bus = SMBus(1)
    found_addr = None
    
    # SCANNER LOOP
    print("      00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f")
    for row in range(0, 128, 16):
        sys.stdout.write(f"   {row:02x}:")
        for col in range(16):
            addr = row + col
            if addr < 0x03 or addr > 0x77:
                sys.stdout.write("   ")
                continue
            
            try:
                # Try reading a byte
                bus.read_byte(addr)
                sys.stdout.write(f" {addr:02X}")
                found_addr = addr
            except OSError:
                sys.stdout.write(" --")
        sys.stdout.write("\n")
        
    if found_addr:
        print(f"\n   ✨ Found Device at: 0x{found_addr:02X}")
        if found_addr == QT2120_ADDRESS:
            print("      (Matches Default QT2120 Address!)")
            # Try Chip ID check only if address matches or we force it
            try:
                chip_id = bus.read_byte_data(found_addr, REG_CHIP_ID)
                print(f"      Chip ID: 0x{chip_id:02X}")
            except:
                print("      Could not read Chip ID.")
            return True
        else:
            print(f"      ⚠️ Address mismatch (Expected 0x{QT2120_ADDRESS:02X})")
            print(f"      Please update driver.py to use address 0x{found_addr:02X}")
            return False
    else:
        print("\n   ❌ No devices found on bus.")
        print("      Check Wiring: SDA->Pin3, SCL->Pin5")
        return False
    
    bus.close()
    return False

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
