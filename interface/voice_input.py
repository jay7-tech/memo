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
        # Using base.en for better accuracy on Pi 5 (it has the RAM)
        print("[Voice] Initializing Speech-to-Text Engines...")
        try:
            from faster_whisper import WhisperModel
            model_size = "base.en" 
            print(f"[Voice] Attempting to load Faster-Whisper ({model_size})...")
            self.whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(f"[Voice] ✓ Faster-Whisper ({model_size}) Ready")
        except ImportError:
             print("[Voice] ❌ Faster-Whisper library NOT found. 'pip install faster-whisper' to fix.")
             print("[Voice] Falling back to Vosk (Lower accuracy for dictation).")
        except Exception as e:
            print(f"[Voice] ❌ Faster-Whisper load failed: {e}")
            print("[Voice] Falling back to Vosk.")

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

    def _play_beep(self):
        """Play a beep sound using PyAudio (Silent fail)."""
        try:
            import math
            import struct
            
            # Generate tone
            duration = 0.15 
            freq = 550.0 
            samples = int(self.RATE * duration)
            audio_data = []
            for n in range(samples):
                val = math.sin(2 * math.pi * freq * n / self.RATE)
                audio_data.append(int(val * 32767.0 * 0.3))
            packed_data = struct.pack(f'{len(audio_data)}h', *audio_data)
            
            stream = self.audio.open(
                format=self.FORMAT, channels=self.CHANNELS,
                rate=self.RATE, output=True
            )
            stream.write(packed_data)
            stream.stop_stream()
            stream.close()
        except Exception:
            # Silent fail for "No Default Output Device" errors on Pi w/o speakers
            pass

    def _run_loop(self):
        """Main loop: Wake Word -> Command."""
        try:
             # Calibrate on startup
             self.calibrate_mic()
        except:
             pass

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
                        self._play_beep()
                            
                        self._listen_for_command(stream)

                        if self.on_processing:
                            self.on_processing()
                        
                        # Reset wake recognizer
                        self.wake_recognizer.Reset()
                        print("[Voice] 👂 Listening for Wake Word...")
                        
            except Exception as e:
                print(f"[Voice] Loop Error: {e}")
                pass

    def calibrate_mic(self, seconds=1.0):
        """Measure ambient noise level to set dynamic threshold."""
        print(f"[Voice] 🎤 Calibrating microphone ({seconds}s)...")
        stream = self.audio.open(
            format=self.FORMAT, channels=self.CHANNELS,
            rate=self.RATE, input=True,
            frames_per_buffer=self.CHUNK
        )
        
        buffer = []
        import math
        import numpy as np

        chunks = int(self.RATE * seconds / self.CHUNK)
        for _ in range(chunks):
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            buffer.append(data)
            
        stream.stop_stream()
        stream.close()
        
        # Calculate Energy
        energies = []
        for chunk in buffer:
            amp = np.frombuffer(chunk, dtype=np.int16)
            energies.append(np.abs(amp).mean())
            
        avg_noise = sum(energies) / len(energies) if energies else 0
        
        # Set Threshold (Noise + Margin)
        # Margin ensures we don't trigger on air conditioner hum
        self.energy_threshold = max(300, avg_noise * 1.5)  # Minimum 300 to avoid super-sensitivity
        print(f"[Voice] Noise Floor: {avg_noise:.1f} | Threshold Set: {self.energy_threshold:.1f}")
        return self.energy_threshold

    def _listen_for_command(self, stream):
        """Record and process command after wake word."""
        print("[Voice] 🔴 Recording command... (Speak Now)")
        audio_buffer = []
        silence_frames = 0
        speech_started = False
        max_duration_frames = int(10 * self.RATE / self.CHUNK) # 10s max
        
        # Dynamic Threshold (Use calibrated value)
        THRESHOLD = getattr(self, 'energy_threshold', 400)
        
        for _ in range(max_duration_frames):
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            audio_buffer.append(data)
            
            # Simple Energy VAD
            import numpy as np
            amp = np.frombuffer(data, dtype=np.int16)
            energy = np.abs(amp).mean()
            
            if energy > THRESHOLD:
                speech_started = True
                silence_frames = 0
            else:
                silence_frames += 1
            
            # Logic:
            # 1. Wait up to 3s for speech to START
            # If threshold is high, speech_started never becomes True -> Timeout
            if not speech_started and len(audio_buffer) > (3 * self.RATE / self.CHUNK):
                print(f"[Voice] Timeout: Energy {energy:.1f} < Threshold {THRESHOLD:.1f}")
                return
                
            # 2. Stop if 1.0s silence AFTER speech started
            if speech_started and silence_frames > (1.0 * self.RATE / self.CHUNK):
                break
        
        if speech_started:
            # Play stop-listening beep
            self._play_beep()
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

