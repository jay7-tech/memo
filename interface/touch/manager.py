import time
import threading
import sys
import os

# Ensure root is in path
sys.path.append(os.getcwd())

from core.engine import get_event_bus, Event, EventType

class TouchChannel:
    """Helper to manage state for a single sensor."""
    def __init__(self, name, driver):
        self.name = name
        self.driver = driver
        self.tap_count = 0
        self.last_tap_time = 0
        self.in_transaction = False
        self.is_pressed = False
        self.consecutive_presses = 0
        # "paper like touch connected to a wire" = ANTENNA.
        # We need massive filtering. 
        # 2 cycles * 50ms loop = 100ms hold required.
        # Reduced from 5 to 2 to improve responsiveness.
        self.required_persistence = 2
        
    def poll(self, now, tap_gap_ms):
        if not self.driver or not self.driver.connected:
            return 0
            
        keys = self.driver.read_keys()
        # Mask inputs (Keys 0-2 only)
        masked_keys = keys & 0x07
        raw_pressed = (masked_keys > 0)
        
        # 1. Noise Filter
        if raw_pressed:
            self.consecutive_presses += 1
        else:
            self.consecutive_presses = 0
            
        pressed = (self.consecutive_presses >= self.required_persistence)
        
        # 2. State Machine
        if pressed and not self.is_pressed:
            # PRESS START
            if not self.in_transaction:
                self.in_transaction = True
                self.tap_count = 1
                self.last_tap_time = now
                print(f"[{self.name}] Tap 1 Started")
            else:
                self.tap_count += 1
                self.last_tap_time = now
                print(f"[{self.name}] Tap {self.tap_count} Started")
            self.is_pressed = True
            
        elif not pressed and self.is_pressed:
            # RELEASE
            self.is_pressed = False
            print(f"[{self.name}] Release. Waiting...")
            
        # 3. Transaction Timeout (Fire Event)
        if self.in_transaction and not self.is_pressed:
             if (now - self.last_tap_time > (tap_gap_ms / 1000.0)):
                 result = self.tap_count
                 self.tap_count = 0
                 self.in_transaction = False
                 return result
                 
        return 0

class TouchManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.event_bus = get_event_bus()
        
        # Config
        self.tap_gap_ms = 700 
        self.left = None
        self.right = None
        
        # Initialize Dual Drivers
        try:
            from .driver import QT2120
            
            # Left Sensor (Bus 1)
            print("[Touch] Init Left Sensor (Bus 1)...")
            driver_l = QT2120(bus_id=1)
            if driver_l.connected:
                 self.left = TouchChannel("Touch_Left", driver_l)
            else:
                 print("[Touch] Left Sensor NOT found.")
            
            # Right Sensor (Bus 3 - Software I2C)
            # Make sure overlay is loaded!
            print("[Touch] Init Right Sensor (Bus 3)...")
            driver_r = QT2120(bus_id=3)
            if driver_r.connected:
                self.right = TouchChannel("Touch_Right", driver_r)
            else:
                print("[Touch] Right Sensor NOT found (Did you run enable_dual_touch.sh and reboot?).")
            
            if not self.left and not self.right:
                print("[Touch] No sensors connected. Touch Disabled.")
            else:
                print(f"[Touch] Ready.")

        except Exception as e:
            print(f"[Touch] Init Error: {e}")

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[Touch] Manager Started (Dual Channel).")

    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1.0)
        # Close drivers
        if self.left and self.left.driver: self.left.driver.close()
        if self.right and self.right.driver: self.right.driver.close()

    def _run_loop(self):
        while self.running:
            now = time.time()
            
            # Poll Left
            if self.left:
                gest = self.left.poll(now, self.tap_gap_ms)
                if gest > 0: self._handle_gesture("left", gest)
                
            # Poll Right
            if self.right:
                gest = self.right.poll(now, self.tap_gap_ms)
                if gest > 0: self._handle_gesture("right", gest)
                
            time.sleep(0.05) # 20Hz

    def _handle_gesture(self, side, count):
        print(f"[Touch] {side.upper()} Sensor: {count} Taps")
        
        if side == "left":
            # Original Controls
            if count == 1:
                self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'toggle_focus'}))
            elif count == 2:
                self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'selfie'}))
            elif count == 3:
                self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'sleep_mode'}))
        
        elif side == "right":
            # New Secondary Controls
            # 1 Tap: Toggle Voice (Mute/Unmute)
            if count == 1:
                print(">> [Action] Right Tap 1: Toggle Voice")
                self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'toggle_voice'}))
            # 2 Taps: Logs Toggle?
            elif count == 2:
                 print(">> [Action] Right Tap 2: Toggle Logs (Future)")
