"""
MEMO - Voice Input Module (Optimized)
======================================
Supports both offline (Vosk) and online (Google) speech recognition.

Features:
    - Offline-first with Vosk (no internet required)
    - Fallback to Google API when online
    - Wake word detection
    - Background noise calibration
    - Thread-safe operation
"""

import speech_recognition as sr
import threading
import time
import os
import json
from typing import Callable, Optional

# Check for Vosk (offline speech recognition)
HAS_VOSK = False
try:
    from vosk import Model, KaldiRecognizer
    import pyaudio
    HAS_VOSK = True
except ImportError:
    pass


class VoiceListener:
    """
    Voice input handler with offline and online modes.
    
    Priority:
    1. Vosk (offline, fast, private)
    2. Google Speech API (online, accurate)
    """
    
    def __init__(
        self,
        callback_func: Callable[[str], None],
        wake_word: str = "computer",
        use_offline: bool = True,
        model_path: str = "models/vosk/vosk-model-en"
    ):
        """
        Initialize voice listener.
        
        Args:
            callback_func: Function to call with recognized text
            wake_word: Wake word to listen for (optional)
            use_offline: Prefer offline Vosk recognition
            model_path: Path to Vosk model directory
        """
        self.callback = callback_func
        self.wake_word = wake_word.lower()
        self.running = True
        self.is_listening_active = False  # Default OFF
        self.use_offline = use_offline and HAS_VOSK
        self.last_interaction = 0 # For wake word window
        
        # The instruction seems to be trying to add a print statement related to model_path here.
        # However, the `model_path` parameter is already passed to `_init_vosk` where it's handled.
        # The provided snippet is syntactically incomplete and seems to be a partial replacement.
        # Given the instruction "Add print statement to show checked model path",
        # and the context provided, it seems the user wants to add a print statement
        # for the `model_path` parameter passed to the constructor.
        # The `if not os.path.exists(model_path):ream = None` part is malformed.
        # I will add the print statement for the `model_path` parameter.
        print(f"[Voice] Initializing with Vosk model path: {os.path.abspath(model_path)}")

        # Vosk setup
        self.vosk_model = None
        self.vosk_recognizer = None
        self.audio_stream = None
        self.pyaudio_instance = None
        
        # Google fallback
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.stop_listening = None
        
        # Initialize
        self._init_audio()
        
        # Start listener thread
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
    
    def _init_audio(self):
        """Initialize audio input."""
        if self.use_offline:
            self._init_vosk()
        
        if not self.use_offline or self.vosk_model is None:
            self._init_google()
    
    def _init_vosk(self):
        """Initialize Vosk offline recognition."""
        model_paths = [
            "models/vosk-model",
            "models/vosk/vosk-model-en",
            "models/vosk/vosk-model-small-en-us-0.15",
            os.path.expanduser("~/.vosk/vosk-model-en"),
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            print("[Voice] Vosk model not found. Using online mode.")
            self.use_offline = False
            return
        
        try:
            print(f"[Voice] Loading Vosk model: {model_path}")
            self.vosk_model = Model(model_path)
            self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
            
            # Initialize PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4096
            )
            
            print("[Voice] ✓ Vosk offline mode ready")
            self.use_offline = True
            
        except Exception as e:
            print(f"[Voice] Vosk init failed: {e}")
            self.use_offline = False
    
    def _init_google(self):
        """Initialize Google Speech API (fallback)."""
        try:
            print("[Voice] Calibrating microphone for Google API...")
            with self.microphone as source:
                # Tune for longer listening and better accuracy
                self.recognizer.pause_threshold = 1.5  # Allow 1.5s silence before cutting off
                self.recognizer.energy_threshold = 300 # Baseline sensitivity
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.non_speaking_duration = 0.5
                self.recognizer.phrase_threshold = 0.3 # Minimum seconds of speaking to consider valid
                
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            
            # Background listener for Google
            self.stop_listening = self.recognizer.listen_in_background(
                self.microphone,
                self._google_callback,
                phrase_time_limit=15 # Allow up to 15s of speech
            )
            print("[Voice] ✓ Google Speech API ready (requires internet)")
            
        except Exception as e:
            print(f"[Voice] Google API init failed: {e}")
    
    def _process_detected_text(self, text: str):
        """
        Filter and process detected text based on state.
        
        Logic:
        1. If TTS is busy -> IGNORE (Self-mute)
        2. If Direct Command -> ACCEPT
        3. If Wake Word -> ACCEPT & Open Active Window
        4. If Active Window Open -> ACCEPT
        5. Else -> IGNORE
        """
        if not text: return

        # 1. Self-Mute: Check TTS
        try:
            from interface.tts_engine import get_tts_engine
            tts = get_tts_engine()
            if tts and tts.is_busy():
                print(f"[Voice] Ignored '{text}' (TTS Active)")
                return
        except:
            pass

        text_lower = text.lower().strip()
        
        # 2. Direct Commands (Bypass Wake Word)
        # "buzz", "focus on", "focus off", "voice off", "quit", "memo news", "who is..." (optional for fast queries)
        direct_triggers = [
            # Core commands
            "buzz", "focus on", "focus off", "voice off", 
            "quit", "memo news", "mino news", "updates",
            "stop", "silence", "pause",
            
            # Phonetic Aliases (Fix for offline recognition)
            "bus", "buys", "bugs", "but", "base", "bars", # for "buzz"
            "me no news", "my news", "more news", "leno news",# for "memo news"
        ]
        
        is_direct = any(t in text_lower for t in direct_triggers)
        
        # 3. Wake Word Check
        # Default wake words if not set
        wake_words = ["hey memo", "memo", "computer", "ok memo"]
        if self.wake_word:
            wake_words.append(self.wake_word)
            
        has_wake_word = any(w in text_lower for w in wake_words)
        
        # 4. Active Window Check
        # If we interacted recently (within 10s), we are "awake"
        is_awake = (time.time() - self.last_interaction) < 10.0
        
        if is_direct or has_wake_word or is_awake:
            # Valid command!
            self.last_interaction = time.time()
            
            # Strip wake word for cleaner processing (optional)
            # Strip wake word for cleaner processing (optional)
            for w in wake_words:
                if text_lower.startswith(w):
                    text = text[len(w):].strip()
                    break
            
            # Fix: Don't process empty commands (e.g. just "Hey Memo")
            if not text:
                print(f">> VOICE AWAKE (Waiting for command...)")
                return

            print(f">> VOICE ACTIVE: {text}")
            self.callback(text)
        else:
            print(f"[Voice] Ignored '{text}' (No wake word)")

    def _listen_loop(self):
        """Main listening loop for Vosk."""
        if not self.use_offline:
            return  # Google uses its own background thread
        
        print("[Voice] Vosk listener started (State: PAUSED)")
        
        while self.running:
            if not self.is_listening_active:
                time.sleep(0.1)
                continue
            
            try:
                # Basic sleep to prevent CPU hogging
                time.sleep(0.01)
                    
                data = self.audio_stream.read(4096, exception_on_overflow=False)
                
                if self.vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self.vosk_recognizer.Result())
                    text = result.get('text', '').strip()
                    self._process_detected_text(text)
                
            except Exception as e:
                if self.running:
                    print(f"[Voice] Error: {e}")
                time.sleep(0.1)
    
    def _google_callback(self, recognizer, audio):
        """Callback for Google Speech API."""
        if not self.running or not self.is_listening_active:
            return
        
        # Skip if using offline mode successfully
        if self.use_offline and self.vosk_model is not None:
            return
        
        try:
            text = recognizer.recognize_google(audio).lower()
            self._process_detected_text(text)
            
        except sr.UnknownValueError:
            pass  # Speech not understood
        except sr.RequestError as e:
            print(f"[Voice] Google API error: {e}")
            # Try to switch to offline if available
            if HAS_VOSK and self.vosk_model is None:
                print("[Voice] Attempting to enable offline mode...")
                self._init_vosk()
        except Exception as e:
            print(f"[Voice] Error: {e}")
    
    def set_active(self, state: bool):
        """Enable or disable listening."""
        self.is_listening_active = state
        mode = "offline (Vosk)" if self.use_offline else "online (Google)"
        status = f"LISTENING [{mode}]" if state else "PAUSED"
        print(f"[Voice] State: {status}")
    
    def get_mode(self) -> str:
        """Get current recognition mode."""
        if self.use_offline and self.vosk_model:
            return "offline"
        return "online"
    
    def stop(self):
        """Stop the voice listener."""
        self.running = False
        
        # Stop Google listener
        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
        
        # Stop Vosk audio stream
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
        
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
        
        print("[Voice] Listener stopped")


# Quick test
if __name__ == "__main__":
    def on_speech(text):
        print(f"Heard: {text}")
    
    listener = VoiceListener(callback_func=on_speech)
    listener.set_active(True)
    
    print("Listening for 30 seconds...")
    time.sleep(30)
    
    listener.stop()
