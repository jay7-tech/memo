import time
import threading
import sys
import os

# Ensure root is in path
sys.path.append(os.getcwd())

from core.engine import get_event_bus, Event, EventType

class TouchManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.driver = None
        self.event_bus = get_event_bus()
        
        # Logic State
        self.tap_count = 0
        self.last_tap_time = 0
        self.in_transaction = False
        self.is_pressed = False
        
        # Config
        self.tap_gap_ms = 400 # Max time between taps to count as sequence
        self.hold_ms = 1000 # Time for HOLD event? (Future)
        
        # Try Loading Driver
        try:
            from .driver import QT2120
            self.driver = QT2120()
            if not self.driver.connected:
                print("[Touch] Driver failed connection. Touch disabled.")
                self.driver = None
        except Exception as e:
            print(f"[Touch] Manager Init Error: {e}")
            self.driver = None

    def start(self):
        if not self.driver: 
            return
        if self.running: 
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[Touch] Manager Started (Listening for Taps).")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.driver:
            self.driver.close()

    def _run_loop(self):
        print(f"[Touch] Entering poll loop. Keys at start: {self.driver.read_keys()}")
        while self.running:
            keys = self.driver.read_keys()
            now = time.time()
            
            # Simple "Any Key" logic
            pressed = (keys > 0)
            
            # DEBUG: Print press state changes
            if pressed and not self.is_pressed:
                print(f"[Touch] DEBUG: Key Pressed! (Mask: {keys})")
            
            if pressed and not self.is_pressed:
                # PRESS EVENT
                self.is_pressed = True
                self.tap_count += 1
                self.last_tap_time = now
                self.in_transaction = True
                # print(f"[Touch] Press! (Count: {self.tap_count})")
                
            elif not pressed and self.is_pressed:
                # RELEASE EVENT
                self.is_pressed = False
                
            # Check Timeout for Tap Transaction
            if self.in_transaction and (now - self.last_tap_time > (self.tap_gap_ms / 1000.0)):
                if not self.is_pressed: # Only fire if released
                    self._fire_gesture(self.tap_count)
                    self.tap_count = 0
                    self.in_transaction = False
            
            # Reset crazy counts
            if self.tap_count > 5: 
                self.tap_count = 0
                self.in_transaction = False
                
            time.sleep(0.05) # 20Hz polling

    def _fire_gesture(self, count):
        print(f"[Touch] Gesture Detected: {count} Taps")
        
        # Map to specific events based on user plan
        # 1 Tap: Toggle Focus Mode
        # 2 Taps: Selfie
        # 3 Taps: Sleep Mode
        
        if count == 1:
            self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'toggle_focus'}))
        elif count == 2:
            self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'selfie'}))
        elif count == 3:
            self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'sleep_mode'}))
