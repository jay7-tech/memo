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
                # OPTIMIZATION: Skip audio processing if TTS is speaking
                from interface.tts_engine import get_tts_engine
                tts = get_tts_engine()
                if tts and tts.is_busy():
                    time.sleep(0.1)
                    continue
                    
                data = self.audio_stream.read(4096, exception_on_overflow=False)
                
                if self.vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self.vosk_recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        print(f">> VOICE (offline): {text}")
                        self.callback(text)
                
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
            print(f">> VOICE (online): {text}")
            self.callback(text)
            
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
