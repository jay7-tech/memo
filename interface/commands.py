
from typing import Optional, Tuple
import time

class SystemCommandHandler:
    """Centralizes system-level command handling to ensure consistency."""
    
    @staticmethod
    def normalize(cmd: str) -> str:
        if not cmd: return ""
        return str(cmd).strip().lower()

    @staticmethod
    def handle_system_command(app, cmd: str) -> bool:
        """
        Returns True if command was handled by system.
        Returns False if it should be passed to AI/Query handler.
        """
        cmd_norm = SystemCommandHandler.normalize(cmd)
        print(f"[SysCmd] Processing: '{cmd_norm}'")
        
        # --- Voice Toggle ---
        if cmd_norm == 'voice toggle':
             if app.voice_input:
                 new_state = not app.voice_input.is_listening_active
                 app.voice_input.set_active(new_state)
                 app.scene_state.voice_active = new_state
                 status = "enabled" if new_state else "disabled"
                 print(f">> SYSTEM: Voice {status}")
                 app.speak(f"Voice input {status}")
                 if new_state: app.lcd.play("listening", loop=True)
                 else: app.lcd.play("silence", loop=True)
             return True

        # --- IDLE MODE (Replaces Sleep) ---
        if cmd_norm == 'idle':
            print(">> SYSTEM: Entering IDLE MODE (Clock)")
            # 1. Vision OFF
            app.vision_active = False
            # 2. Voice OFF
            if app.voice_input: app.voice_input.set_active(False)
            app.scene_state.voice_active = False
            # 3. LCD Clock
            app.lcd.set_clock_mode(True)
            # 4. Speak
            app.speak("Entering Idle Mode. Time to chill.")
            return True

        # --- WAKE UP ---
        if cmd_norm in ['wake', 'wakeup']:
            print(">> SYSTEM: Waking up!")
            # 1. Vision ON
            app.vision_active = True
            # 2. Voice ON
            if app.voice_input: app.voice_input.set_active(True)
            app.scene_state.voice_active = True
            # 3. LCD Normal
            app.lcd.set_clock_mode(False)
            # 4. Speak
            app.speak("I'm back! Ready to go.")
            return True

        # --- FOCUS MODE ---
        if cmd_norm == 'focus on':
            app.scene_state.focus_mode = True
            print(">> SYSTEM: Focus Mode ENABLED")
            app.speak("Focus mode on! No distractions.")
            app.lcd.set_focus_mode(True)
            return True
            
        if cmd_norm == 'focus off':
            app.scene_state.focus_mode = False
            print(">> SYSTEM: Focus Mode DISABLED")
            app.speak("Focus mode off. Relax.")
            app.lcd.set_focus_mode(False)
            return True
            
        # --- SHUTDOWN ---
        if cmd_norm in ['quit', 'exit', 'shutdown']:
            print(">> SYSTEM: Shutdown Initiated")
            app.speak("System shutting down.")
            app.running = False
            return True

        return False
