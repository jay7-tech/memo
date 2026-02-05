
import time
import threading

# Try import smbus
try:
    from smbus2 import SMBus
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False
    print("[Touch] ⚠️ smbus2 not installed. Touch will fail.")

# QT2120 Registers (Based on Datasheet / User Snippet)
QT2120_ADDRESS = 0x1C # Default address
REG_CHIP_ID = 0x00
REG_RESET = 0x04 # Write non-zero to reset? Snippet says write 0x01 bytes to RESET cmd
# Actually standard QT2120:
# 0x00: Chip ID
# 0x01: Version
# 0x02: Status (Bit 7=Calibrating)
# 0x03: Detection Status (Keys)
# 0x04: Key Status 2 (if >8 keys?) -- User snippet reads KeyStatus 1 & 2. 
# Let's trust snippet mapping if possible, but snippet is a bit raw.
# Snippet: I2Cread( QT2120_I2C_ADDRESS, QT2120_KEYSTATUS_1, 1, &data);
# Registers:
REG_DETECTION_STATUS = 0x02
REG_KEY_STATUS_1 = 0x03
REG_KEY_STATUS_2 = 0x04
REG_SLIDER = 0x05
REG_CALIBRATE = 0x06 # Write non-zero to trigger
REG_RESET = 0x07 # Write non-zero
REG_LP = 0x08 # Low Power Mode

class QT2120:
    def __init__(self, bus_id=1, address=QT2120_ADDRESS):
        self.bus_id = bus_id
        self.address = address
        self.bus = None
        self.connected = False
        
        if not I2C_AVAILABLE:
            return

class QT2120:
    def __init__(self, bus_id=1, address=QT2120_ADDRESS):
        self.bus_id = bus_id
        self.address = address
        self.bus = None
        self.connected = False
        
        if not I2C_AVAILABLE:
            return

        try:
            self.bus = SMBus(bus_id)
            # Check Chip ID
            chip_id = self.read_reg(REG_CHIP_ID)
            print(f"[Touch] Chip ID: 0x{chip_id:02X}")
            if chip_id == 0x3E: # Expected ID for QT2120
                print("[Touch] ✓ QT2120 Connected")
                self.connected = True
                self.reset()
                print("[Touch] ✓ QT2120 Connected")
                self.connected = True
                self.reset()
                
                # --- Configuration for STABILITY ---
                # 1. Thresholds (NTHR): 255 = Max Resistance to press.
                #    Registers 0x0A - 0x15
                self.set_threshold(150) # Start with safe high value (200 might be too hard)
                 
                # 2. Calibration
                self.calibrate()
            else:
                print(f"[Touch] ❌ ID Mismatch (Exp 0x3E, Got 0x{chip_id:02X}). Wiring issue?")
        except Exception as e:
            print(f"[Touch] Init Error: {e}")
            self.connected = False

    def set_threshold(self, value):
        """Set detection threshold (0-255). Registers 0x0A-0x15 for Keys 0-11."""
        # Clamp value
        value = max(10, min(255, value))
        print(f"[Touch] Setting threshold to {value} for ALL keys (0x0A-0x15)")
        # QT2120: NTHR for Keys 0-11 are at addresses 10 (0x0A) to 21 (0x15)
        for reg in range(0x0A, 0x16): 
            self.write_reg(reg, value)
            
    # def set_integrator(self, value):
    #    """Integrator filter (DI). Address uncertain, disabling to prevent issues."""
    #    pass

    def read_reg(self, reg):
        try:
            return self.bus.read_byte_data(self.address, reg)
        except:
            return 0

    def write_reg(self, reg, val):
        try:
            self.bus.write_byte_data(self.address, reg, val)
        except:
            pass

    def reset(self):
        """Soft reset key."""
        # User snippet: I2Cwrite_Multibyte(ADDR, RESET, &dat, 1) where reset is 0x07?
        # Datasheet confirms 0x07 is Reset. Write nonzero.
        print("[Touch] Resetting chip...")
        self.write_reg(REG_RESET, 0x55) # Any non-zero?
        time.sleep(0.15) # Wait for wake

    def calibrate(self):
        """Force recalibration."""
        print("[Touch] Calibrating...")
        self.write_reg(REG_CALIBRATE, 0x01)
        # Wait until bit 7 of Status (0x02) clears?
        for _ in range(20):
            status = self.read_reg(REG_DETECTION_STATUS)
            if not (status & 0x80):
                # print("[Touch] Calibrated.")
                return
            time.sleep(0.05)
        print("[Touch] Calibration timeout.")

    def read_keys(self):
        """
        Return integer bitmask of pressed keys (0-11).
        User code reads status 1 and status 2 if index > 7.
        Usually 0x03 has bits 0-7, 0x04 has bits 8-11.
        """
        if not self.connected: return 0
        
        try:
            low = self.read_reg(REG_KEY_STATUS_1)
            high = self.read_reg(REG_KEY_STATUS_2)
            
            # User snippet mentions checking specific bit for specific key index.
            # Combined mask:
            # Low: K0..K7
            # High: K8..K11 (lower nibble?)
            mask = low | (high << 8)
            return mask
        except:
            return 0

    def close(self):
        if self.bus:
            self.bus.close()
