"""
MEMO - High-Fidelity Speech Recognition (Pro)
==============================================
Production-grade voice pipeline optimized for Edge/Pi.

Features:
- Real-time VAD (Voice Activity Detection) using WebRTC
- Bandpass noise filtering (300-3400Hz)
- Faster-Whisper (CTranslate2) for accurate transcription
- Latency-aware buffering

Usage:
    transcriber = HighFidelityTranscriber(model_size="tiny.en")
    transcriber.start()
    
    # In your main loop:
    text = transcriber.get_last_text()
    if text:
        process(text)
"""

import os
import time
import threading
import queue
import collections
import numpy as np
import pyaudio
import wave

# Audio Processing
HAS_VAD = False
try:
    import webrtcvad
    from scipy import signal
    HAS_VAD = True
except ImportError:
    print("[SpeechPro] VAD/Scipy missing. Using Energy VAD fallback.")

# Optimize environment for reduced latency
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["CT2_VERBOSE"] = "0"


class AudioPreprocessor:
    """Handles signal processing: filtering and normalization."""
    
    def __init__(self, rate=16000):
        self.rate = rate
        self.sos = None
        if HAS_VAD:
            try:
                # Bandpass filter for human voice (300Hz - 3400Hz)
                self.sos = signal.butter(10, [300, 3400], 'bandpass', fs=rate, output='sos')
            except:
                pass

    def process(self, audio_data: bytes) -> np.ndarray:
        """Apply bandpass filter and normalize audio."""
        if not self.sos:
            return np.frombuffer(audio_data, dtype=np.int16)
            
        # Convert bytes to float32 numpy array
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # Apply precise bandpass filter
        filtered = signal.sosfilt(self.sos, audio_np)
        
        return filtered.astype(np.int16)


class HighFidelityTranscriber:
    """
    Robust Speech-to-Text Engine.
    Uses producer-consumer architecture for zero-dropped-frames.
    """
    
    def __init__(self, 
                 callback_func=None,
                 wake_word: str = "computer",
                 use_offline: bool = True,
                 model_path: str = None, 
                 model_size: str = "tiny.en", 
                 device: str = "auto",
                 compute_type: str = "int8"):
        
        self.rate = 16000
        self.chunk_duration_ms = 30 # WebRTC VAD requires 10, 20, or 30ms
        self.chunk_size = int(self.rate * self.chunk_duration_ms / 1000)
        
        self.running = False
        self.is_listening_active = False
        self.last_interaction = 0
        self.callback = callback_func
        self.wake_word = wake_word.lower() if wake_word else None
        
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        
        # VAD Init
        self.vad = None
        if HAS_VAD:
            try:
                self.vad = webrtcvad.Vad(3)
            except:
                pass
                
        self.preprocessor = AudioPreprocessor(self.rate)
        
        # Init Model Strategy
        self.engine_type = "none"
        self.model = None
        
        # 1. Try Faster-Whisper (Optimized)
        try:
            print(f"[SpeechPro] Loading Faster-Whisper ({model_size})...")
            from faster_whisper import WhisperModel
            
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
            print(f"[SpeechPro] Using Device: {device} | Precision: {compute_type}")
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            self.engine_type = "faster"
            print("[SpeechPro] ✓ Faster-Whisper Ready")
        except Exception as e:
            print(f"[SpeechPro] Faster-Whisper failed: {e}")
            print("[SpeechPro] Falling back to Standard Whisper...")
            
            # 2. Fallback to OpenAI Whisper (Standard)
            try:
                import whisper
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"[SpeechPro] Loading OpenAI Whisper ({model_size}) on {device}...")
                self.model = whisper.load_model(model_size, device=device)
                self.engine_type = "standard"
                print("[SpeechPro] ✓ OpenAI Whisper Ready")
            except Exception as e2:
                print(f"[SpeechPro] Standard Whisper failed: {e2}")
                # Don't raise error, just fallback to dummy mode or allow retry
                print("!! CRITICAL: No Speech Engine. Voice will be disabled.")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback - critical path - keep extremely fast."""
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def start(self):
        """Start capture and processing threads."""
        self.running = True
        
        # 1. Start Capture
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )
        self.stream.start_stream()
        
        # 2. Start Processor
        self.proc_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.proc_thread.start()
        
        engine_name = "Faster-Whisper" if self.engine_type == "faster" else "OpenAI-Whisper"
        print(f"[SpeechPro] 🎙️  Listening ({engine_name})...")

    def stop(self):
        """Graceful shutdown."""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

    def _process_loop(self):
        """
        Consumes raw audio chunks, detects speech segments, and transcribes.
        Logic: Accumulate chunks -> Detect VAD -> Group Speech -> Transcribe
        """
        ring_buffer = collections.deque(maxlen=20) # 600ms buffer for context
        triggered = False
        speech_frames = []
        
        # Tuning
        SILENCE_LIMIT_MS = 500  # Voice pause to consider sentence end
        silence_counter = 0
        limit_chunks = int(SILENCE_LIMIT_MS / self.chunk_duration_ms)
        
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue
                
            # 1. VAD Check (Hybrid)
            is_speech = False
            
            if self.vad:
                try:
                    is_speech = self.vad.is_speech(chunk, self.rate)
                except:
                    is_speech = False
            else:
                # Energy Fallback
                import numpy as np
                amp = np.frombuffer(chunk, dtype=np.int16)
                if np.abs(amp).mean() > 300: # Threshold needs tuning
                    is_speech = True
            
            # 2. Logic to build sentences
            if not triggered:
                ring_buffer.append((chunk, is_speech))
                
                # Trigger if we see enough continuous speech
                # e.g. 90% of last 300ms is speech
                num_voiced = sum(1 for c, v in ring_buffer if v)
                if num_voiced > 0.8 * len(ring_buffer) and len(ring_buffer) > 10:
                    triggered = True
                    # Flush buffer into speech frames
                    for c, v in ring_buffer:
                        speech_frames.append(c)
                    ring_buffer.clear()
                    # print("[>] Voice Start")
            else:
                # We are recording a sentence
                speech_frames.append(chunk)
                
                if not is_speech:
                    silence_counter += 1
                else:
                    silence_counter = 0
                    
                # End of sentence detection
                if silence_counter > limit_chunks:
                    triggered = False
                    if speech_frames:
                        self._transcribe(b''.join(speech_frames))
                    speech_frames = []
                    silence_counter = 0
                    # print("[<] Voice End")

    # Compatible API with VoiceListener
    def set_active(self, state: bool):
        """Enable or disable listening."""
        self.is_listening_active = state
        status = "LISTENING" if state else "PAUSED"
        print(f"[SpeechPro] State: {status}")

    def get_mode(self) -> str:
        return "offline (Whisper)"

    def _process_detected_text(self, text: str):
        """
        Filter and process detected text based on state.
        Ported from VoiceListener for Hybrid Logic.
        """
        if not text: return

        # 1. Self-Mute: Check TTS
        try:
            from interface.tts_engine import get_tts_engine
            tts = get_tts_engine()
            if tts and tts.is_busy():
                print(f"[SpeechPro] Ignored '{text}' (TTS Active)")
                return
        except:
            pass

        text_lower = text.lower().strip()
        
        # 2. Direct Commands (Bypass Wake Word)
        direct_triggers = [
            "buzz", "focus on", "focus off", "voice off", 
            "quit", "memo news", "mino news", "updates",
            "stop", "silence", "pause"
        ]
        
        is_direct = any(t in text_lower for t in direct_triggers)
        
        # 3. Wake Word Check
        wake_words = ["hey memo", "memo", "computer", "ok memo"]
        
        has_wake_word = any(w in text_lower for w in wake_words)
        
        # 4. Active Window Check
        # If we interacted recently (within 10s), we are "awake"
        is_awake = (time.time() - self.last_interaction) < 10.0
        
        if is_direct or has_wake_word or is_awake:
            # Valid command!
            self.last_interaction = time.time()
            
            # Strip wake word for cleaner processing (optional)
            for w in wake_words:
                if text_lower.startswith(w):
                    text = text[len(w):].strip()
                    break
            
            # Fix: Don't process empty commands
            if not text:
                print(f">> VOICE AWAKE (Waiting for command...)")
                return

            print(f">> VOICE ACTIVE (Whisper): {text}")
            if self.callback:
                self.callback(text)
            self.text_queue.put(text)
        else:
            print(f"[SpeechPro] Ignored '{text}' (No wake word)")

    def _transcribe(self, audio_data: bytes):
        """Run inference on the collected speech segment."""
        # 1. Clean Audio
        # cleaned = self.preprocessor.process(audio_data) (Optional based on CPU)
        
        # 2. Convert to float32 for Whisper
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # check duration (ignore blips < 0.5s)
        if len(audio_np) < self.rate * 0.5:
            return

        # 3. Inference
        try:
            if self.engine_type == "faster":
                segments, info = self.model.transcribe(
                    audio_np, 
                    beam_size=5, 
                    language="en",
                    condition_on_previous_text=False,
                    vad_filter=True 
                )
                
                for segment in segments:
                    text = segment.text.strip()
                    confidence = segment.avg_logprob
                    # Faster-whisper returns logprob (negative)
                    if text and confidence > -1.5: 
                        print(f" > '{text}' ({info.language_probability:.2f})")
                        self._process_detected_text(text)
                        
            elif self.engine_type == "standard":
                # OpenAI Whisper takes numpy array or path
                result = self.model.transcribe(
                    audio_np, 
                    language="en",
                    fp16=False # Force FP32 if CPU/Numpy issues
                )
                text = result.get('text', '').strip()
                if text:
                    print(f" > '{text}'")
                    self._process_detected_text(text)
                    
        except Exception as e:
            print(f"[SpeechPro] Transcription Error: {e}")

    def get_text(self, block=False):
        """Get the latest transcribed text."""
        try:
            return self.text_queue.get(block=block, timeout=0.1)
        except queue.Empty:
            return None


if __name__ == "__main__":
    # Test Routine
    print("Initializing PRO Speech Engine...")
    engine = HighFidelityTranscriber(model_size="tiny.en")
    engine.start()
    
    try:
        while True:
            text = engine.get_text(block=True)
            if text:
                print(f"Captured: {text}")
    except KeyboardInterrupt:
        engine.stop()
