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
    Robust Voice Input with Wake Word & High-Fidelity STT.
    
    Flow:
    1. Listen for Wake Word (OpenWakeWord) -> Low Power
    2. Trigger "Listening" State (VAD)
    3. Capture Command
    4. Transcribe (Faster-Whisper or Vosk)
    """
    
    def __init__(
        self,
        callback_func: Callable[[str], None],
        wake_word: str = "hey_memo", # Ignored in favor of list
        use_offline: bool = True,
        model_path: str = "models/vosk/vosk-model-en",
        on_wake: Optional[Callable] = None,
        on_processing: Optional[Callable] = None
    ):
        self.callback = callback_func
        self.on_wake = on_wake
        self.on_processing = on_processing
        
        self.running = True
        self.is_listening_active = True # Default to active (but waiting for wake word)
        self.use_offline = use_offline
        
        # Audio Config
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1

        self.RATE = 16000
        self.CHUNK = 4096 # Larger chunk for Vosk
        self.audio = pyaudio.PyAudio()
        
        # Custom Wake Words (Grammar)
        self.wake_words = [
            "hey memo", "hey bot",
            "yo memo", "yo bot",
            "memo"
        ]
        
        # STT Engines
        self.whisper_model = None
        self.vosk_recognizer = None
        self.vosk_model = None
        self.wake_recognizer = None
        
        # Find correct path
        valid_path = self._find_model_path(model_path)
        self._init_stt(valid_path)
        
        # Start Thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(f"[Voice] Listener started. Wake Words: {self.wake_words}")

    def _find_model_path(self, default_path):
        """Locate Vosk model in common paths."""
        candidates = [
            default_path,
            "models/vosk-model",
            "models/vosk/vosk-model-en",
            "models/vosk-model-small-en-us-0.15",
            os.path.expanduser("~/.vosk/vosk-model-en")
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return default_path

    def _init_stt(self, vosk_path):
        """Load STT engines."""
        # 1. Faster-Whisper (Command Transcription)
        try:
            from faster_whisper import WhisperModel
            self.whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            print("[Voice] ✓ Faster-Whisper (Tiny) Loaded")
        except Exception as e:
            print(f"[Voice] Faster-Whisper unavailable ({e}). Fallback to Vosk.")

        # 2. Vosk (Wake Word & Fallback)
        if os.path.exists(vosk_path):
            try:
                from vosk import Model, KaldiRecognizer
                self.vosk_model = Model(vosk_path)
                # Wake Word Recognizer (Strict Grammar)
                # Note: Grammar must be JSON list of strings
                grammar = json.dumps(self.wake_words + ["[unk]"])
                self.wake_recognizer = KaldiRecognizer(self.vosk_model, 16000, grammar)
                
                # Command Recognizer (Full Vocabulary)
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
                
                print(f"[Voice] ✓ Vosk Ready (Wake Grammar Active)")
            except Exception as e:
                print(f"[Voice] Vosk Error: {e}")

    def _run_loop(self):
        """Main loop: Wake Word -> Command."""
        stream = self.audio.open(
            format=self.FORMAT, channels=self.CHANNELS,
            rate=self.RATE, input=True,
            frames_per_buffer=self.CHUNK
        )
        
        print("[Voice] 👂 Listening for Wake Word...")
        
        while self.running:
            try:
                # Idle check for efficiency
                if not self.is_listening_active:
                    time.sleep(0.5)
                    continue
                    
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                
                # --- WAKE WORD DETECTION (Vosk Grammar) ---
                if self.wake_recognizer.AcceptWaveform(data):
                    res = json.loads(self.wake_recognizer.Result())
                    text = res.get('text', '')
                    
                    if any(w in text for w in self.wake_words):
                        print(f"\n[Voice] ⚡ WAKE: '{text}'!")
                        
                        if self.on_wake:
                            self.on_wake()

                        # Audio Beep
                        play_wake_beep()
                            
                        self._listen_for_command(stream)

                        if self.on_processing:
                            self.on_processing()
                        
                        # Reset wake recognizer
                        self.wake_recognizer.Reset()
                        print("[Voice] 👂 Listening for Wake Word...")
                        
            except Exception as e:
                # print(f"[Voice] Loop Error: {e}")
                pass

    def _listen_for_command(self, stream):
        """Record and process command after wake word."""
        print("[Voice] 🔴 Recording command... (Speak Now)")
        audio_buffer = []
        silence_frames = 0
        speech_started = False
        max_duration_frames = int(10 * self.RATE / self.CHUNK) # 10s max
        
        for _ in range(max_duration_frames):
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            audio_buffer.append(data)
            
            # Simple Energy VAD
            import numpy as np
            amp = np.frombuffer(data, dtype=np.int16)
            energy = np.abs(amp).mean()
            
            # Dynamic Threshold (adjust based on your mic)
            THRESHOLD = 150 
            
            if energy > THRESHOLD:
                speech_started = True
                silence_frames = 0
            else:
                silence_frames += 1
            
            # Logic:
            # 1. Wait up to 3s for speech to START
            if not speech_started and len(audio_buffer) > (3 * self.RATE / self.CHUNK):
                print("[Voice] Timeout: No speech detected.")
                return
                
            # 2. Stop if 1.0s silence AFTER speech started
            if speech_started and silence_frames > (1.0 * self.RATE / self.CHUNK):
                # print("[Voice] End of speech detected.")
                break
        
        if speech_started:
            # Play stop-listening beep
            try:
                import winsound
                winsound.Beep(800, 150) # Lower beep
            except Exception as e:
                print(f"[Voice] Beep Error: {e}")
            self._process_command(b''.join(audio_buffer))

    def _process_command(self, audio_data):
        """Transcribe audio data."""
        print("[Voice] Processing command...")
        text = ""
        
        # 1. Faster-Whisper
        if self.whisper_model:
            try:
                import numpy as np
                import io
                # Mock file for whisper
                audio_np = np.frombuffer(audio_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0
                segments, _ = self.whisper_model.transcribe(audio_np, beam_size=5)
                text = " ".join([s.text for s in segments]).strip()
            except Exception as e:
                print(f"[Voice] Whisper Fail: {e}")
        
        # 2. Vosk Fallback
        if not text and self.vosk_recognizer:
            try:
                import json
                if self.vosk_recognizer.AcceptWaveform(audio_data):
                    res = json.loads(self.vosk_recognizer.Result())
                    text = res.get('text', '')
                else:
                    res = json.loads(self.vosk_recognizer.FinalResult())
                    text = res.get('text', '')
            except Exception as e:
                 print(f"[Voice] Vosk Fail: {e}")

        if text:
            print(f"[Voice] 🗣️ User said: '{text}'")
            self.callback(text)
        else:
            print("[Voice] 🤷 Could not understand.")

    def set_active(self, state: bool):
        """Enable or disable voice processing."""
        self.is_listening_active = state
        print(f"[Voice] Input {'ENABLED' if state else 'DISABLED'}")

    def stop(self):
        self.running = False

