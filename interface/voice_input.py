import speech_recognition as sr
import threading
import time

class VoiceListener:
    def __init__(self, callback_func, wake_word="computer"):
        self.recognizer = sr.Recognizer()
        self.processed_audio = False
        self.callback = callback_func
        self.wake_word = wake_word.lower()
        self.running = True
        self.is_listening_active = False # Default OFF
        
        # Adjust for ambient noise
        self.microphone = sr.Microphone()
        
        # Start background listener
        print("[Voice] calibrating background noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[Voice] Background listener started (State: PAUSED).")
        
        self.stop_listening = self.recognizer.listen_in_background(self.microphone, self.audio_callback)

    def set_active(self, state):
        self.is_listening_active = state
        status = "LISTENING" if state else "PAUSED"
        print(f"[Voice] State: {status}")

    def audio_callback(self, recognizer, audio):
        if not self.running: return
        
        # If paused, ignore audio processing to privacy/CPU
        if not self.is_listening_active:
            return
        
        try:
            # Recognize speech
            text = recognizer.recognize_google(audio).lower()
            
            # Since we manually toggle listening, we might NOT need wake word strictness?
            # Or keep it optionally. User said "command enables listening".
            # Usually implies push-to-talk style or "Voice Mode ON".
            # We'll pass everything if active.
            
            print(f">> VOICE: {text}")
            self.callback(text)
                 
        except sr.UnknownValueError:
            pass 
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
        except Exception as e:
            print(f"Voice Error: {e}")

    def stop(self):
        self.running = False
        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
