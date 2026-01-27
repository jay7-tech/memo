"""
MEMO - Text-to-Speech Module (Optimized)
=========================================
High-performance TTS with engine reuse and multiple backends.

Features:
    - Single engine instance (no recreation overhead)
    - Thread-safe queue-based processing
    - Multiple backend support (pyttsx3, PowerShell, espeak)
    - Non-blocking and blocking speech modes
    - Raspberry Pi compatible

Backends (in order of preference):
    1. pyttsx3 - Fast, offline, cross-platform
    2. espeak - Linux/Pi native
    3. PowerShell SAPI - Windows built-in
    4. Print-only - Console fallback
"""

import queue
import threading
import subprocess
import sys
import time
from typing import Optional


class TTSEngine:
    """
    High-performance Text-to-Speech engine.
    
    Uses a persistent engine instance to avoid initialization overhead.
    Speech requests are queued and processed in background.
    """
    
    def __init__(self, rate: int = 175, volume: float = 1.0):
        """
        Initialize TTS engine.
        
        Args:
            rate: Speech rate (words per minute)
            volume: Volume level (0.0 to 1.0)
        """
        self.rate = rate
        self.volume = volume
        
        self.queue = queue.Queue()
        self.running = True
        self.worker_thread = None
        
        # Engine instance (reused)
        self._engine = None
        self._engine_lock = threading.Lock()
        self._backend = None
        
        # Initialize backend
        self._init_backend()
    
    def _init_backend(self):
        """Initialize the best available TTS backend."""
        
        # Try pyttsx3 first
        if self._try_pyttsx3():
            return
        
        # Try espeak (Linux/Pi)
        if self._try_espeak():
            return
        
        # Try PowerShell (Windows)
        if sys.platform == 'win32':
            self._backend = 'powershell'
            print("[TTS] Using PowerShell SAPI")
            return
        
        # Fallback to print
        self._backend = 'print'
        print("[TTS] No TTS engine available, using print mode")
    
    def _try_pyttsx3(self) -> bool:
        """Try to initialize pyttsx3."""
        try:
            import pyttsx3
            
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self.rate)
            self._engine.setProperty('volume', self.volume)
            
            # Try to use a natural voice
            voices = self._engine.getProperty('voices')
            for voice in voices:
                name_lower = voice.name.lower()
                if any(v in name_lower for v in ['zira', 'david', 'hazel', 'english']):
                    self._engine.setProperty('voice', voice.id)
                    break
            
            self._backend = 'pyttsx3'
            print("[TTS] ✓ Using pyttsx3 engine")
            return True
            
        except Exception as e:
            print(f"[TTS] pyttsx3 not available: {e}")
            return False
    
    def _try_espeak(self) -> bool:
        """Try to use espeak (Linux/Pi)."""
        try:
            result = subprocess.run(
                ['espeak', '--version'],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                self._backend = 'espeak'
                print("[TTS] ✓ Using espeak")
                return True
        except:
            pass
        return False
    
    def start(self):
        """Start the TTS worker thread."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def _worker(self):
        """Background worker that processes the speech queue."""
        while self.running:
            try:
                text = self.queue.get(timeout=1.0)
                if text is None:
                    break
                
                self._speak_sync(text)
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS Error] {e}")
    
    def _speak_sync(self, text: str):
        """Speak text synchronously using the selected backend."""
        if not text:
            return
        
        with self._engine_lock:
            if self._backend == 'pyttsx3':
                self._speak_pyttsx3(text)
            elif self._backend == 'espeak':
                self._speak_espeak(text)
            elif self._backend == 'powershell':
                self._speak_powershell(text)
            else:
                print(f"🔊 [MEMO says]: {text}")
    
    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3 (reuses engine)."""
        try:
            # Reuse existing engine
            self._engine.say(text)
            self._engine.runAndWait()
        except RuntimeError as e:
            if "run loop already started" in str(e):
                # Engine busy, wait and retry
                time.sleep(0.1)
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except:
                    self._speak_fallback(text)
            else:
                self._speak_fallback(text)
        except Exception as e:
            print(f"[TTS pyttsx3 error] {e}")
            self._speak_fallback(text)
    
    def _speak_espeak(self, text: str):
        """Speak using espeak (Linux/Pi)."""
        try:
            safe_text = text.replace('"', '\\"')
            subprocess.run(
                ['espeak', '-s', str(self.rate), safe_text],
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            print(f"[TTS espeak error] {e}")
            print(f"🔊 [MEMO says]: {text}")
    
    def _speak_powershell(self, text: str):
        """Speak using Windows PowerShell SAPI."""
        try:
            safe_text = text.replace("'", "''").replace('"', '`"')
            cmd = f"Add-Type -AssemblyName System.Speech; " \
                  f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; " \
                  f"$synth.Rate = 2; " \
                  f"$synth.Speak('{safe_text}')"
            
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            print(f"[TTS] Speech timeout: {text[:30]}...")
        except Exception as e:
            print(f"[TTS PowerShell error] {e}")
            print(f"🔊 [MEMO says]: {text}")
    
    def _speak_fallback(self, text: str):
        """Fallback to espeak or print."""
        if sys.platform != 'win32':
            try:
                subprocess.run(['espeak', text], capture_output=True, timeout=10)
                return
            except:
                pass
        print(f"🔊 [MEMO says]: {text}")
    
    def speak(self, text: str):
        """
        Queue text to be spoken (non-blocking).
        
        Args:
            text: Text to speak
        """
        if text:
            print(f"🔊 Speaking: {text}")
            self.queue.put(text)
    
    def speak_now(self, text: str):
        """
        Speak text immediately (blocking).
        
        Args:
            text: Text to speak immediately
        """
        if text:
            print(f"🔊 Speaking: {text}")
            self._speak_sync(text)
    
    def stop(self):
        """Stop the TTS engine."""
        self.running = False
        self.queue.put(None)  # Signal worker to stop
        
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        # Cleanup pyttsx3 engine
        if self._engine and self._backend == 'pyttsx3':
            try:
                self._engine.stop()
            except:
                pass
    
    def is_busy(self) -> bool:
        """Check if TTS is currently speaking."""
        return not self.queue.empty()


# Global instance
_tts_engine: Optional[TTSEngine] = None


def init_tts(rate: int = 175, volume: float = 1.0) -> TTSEngine:
    """
    Initialize the global TTS engine.
    
    Args:
        rate: Speech rate
        volume: Volume level
    
    Returns:
        TTSEngine instance
    """
    global _tts_engine
    _tts_engine = TTSEngine(rate=rate, volume=volume)
    _tts_engine.start()
    return _tts_engine


def speak(text: str):
    """Queue text to be spoken (non-blocking)."""
    global _tts_engine
    if _tts_engine:
        _tts_engine.speak(text)
    else:
        print(f"🔊 [MEMO says]: {text}")


def speak_now(text: str):
    """Speak text immediately (blocking)."""
    global _tts_engine
    if _tts_engine:
        _tts_engine.speak_now(text)
    else:
        print(f"🔊 [MEMO says]: {text}")


def stop_tts():
    """Stop the TTS engine."""
    global _tts_engine
    if _tts_engine:
        _tts_engine.stop()


def get_tts_engine() -> Optional[TTSEngine]:
    """Get the global TTS engine instance."""
    return _tts_engine


# Quick test
if __name__ == "__main__":
    print("Testing TTS Engine...")
    
    engine = init_tts()
    
    # Test queued speech
    speak("Hello! I am MEMO, your desktop companion.")
    speak("This message is queued.")
    
    # Test immediate speech
    speak_now("This message is spoken immediately.")
    
    # Wait for queue to complete
    time.sleep(5)
    
    # Test multiple rapid requests (should not recreate engine)
    for i in range(3):
        speak(f"Rapid message number {i + 1}.")
    
    time.sleep(8)
    
    stop_tts()
    print("TTS test complete.")
