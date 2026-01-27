"""
MEMO - Text-to-Speech Module (Windows-Optimized)
=================================================
Uses Windows SAPI directly for reliable audio output.

Backends:
    1. Windows SAPI (via PowerShell) - Most reliable on Windows
    2. espeak - Linux/Pi
    3. pyttsx3 - Fallback
"""

import queue
import threading
import subprocess
import sys
import time
import os
from typing import Optional


class TTSEngine:
    """
    Reliable Text-to-Speech engine.
    
    Uses Windows SAPI directly for better reliability with threading.
    """
    
    def __init__(self, rate: int = 175, volume: float = 1.0):
        self.rate = rate
        self.volume = volume
        
        self.queue = queue.Queue()
        self.running = True
        self.worker_thread = None
        self._speaking = False
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Detect platform and backend
        self._backend = self._detect_backend()
        print(f"[TTS] ✓ Using {self._backend} engine")
    
    def _detect_backend(self) -> str:
        """Detect the best TTS backend."""
        if sys.platform == 'win32':
            return 'sapi'  # Windows SAPI is most reliable
        
        # Check for espeak on Linux/Pi
        try:
            result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                return 'espeak'
        except:
            pass
        
        # Try pyttsx3
        try:
            import pyttsx3
            return 'pyttsx3'
        except:
            pass
        
        return 'print'
    
    def start(self):
        """Start the TTS worker thread."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def _worker(self):
        """Background worker that processes the speech queue."""
        while self.running:
            try:
                text = self.queue.get(timeout=0.5)
                if text is None:
                    break
                
                self._speak_text(text)
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS Error] {e}")
    
    def _speak_text(self, text: str):
        """Speak text using the selected backend."""
        if not text:
            return
        
        with self._lock:
            self._speaking = True
            try:
                if self._backend == 'sapi':
                    self._speak_sapi(text)
                elif self._backend == 'espeak':
                    self._speak_espeak(text)
                elif self._backend == 'pyttsx3':
                    self._speak_pyttsx3(text)
                else:
                    print(f"🔊 [MEMO]: {text}")
            finally:
                self._speaking = False
    
    def _speak_sapi(self, text: str):
        """Speak using Windows SAPI (most reliable)."""
        try:
            # Escape single quotes
            safe_text = text.replace("'", "''")
            
            # Create a VBS script (more reliable than PowerShell for SAPI)
            vbs_content = f'''
CreateObject("SAPI.SpVoice").Speak "{safe_text.replace('"', '""')}"
'''
            # Write temp VBS file
            vbs_path = os.path.join(os.environ.get('TEMP', '.'), 'memo_speak.vbs')
            with open(vbs_path, 'w') as f:
                f.write(vbs_content)
            
            # Run VBS
            subprocess.run(
                ['cscript', '//nologo', vbs_path],
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
        except subprocess.TimeoutExpired:
            print(f"[TTS] Timeout speaking: {text[:30]}...")
        except Exception as e:
            print(f"[TTS SAPI error] {e}")
            # Fallback to print
            print(f"🔊 [MEMO]: {text}")
    
    def _speak_espeak(self, text: str):
        """Speak using espeak (Linux/Pi)."""
        try:
            subprocess.run(
                ['espeak', '-s', str(self.rate), text],
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            print(f"[TTS espeak error] {e}")
            print(f"🔊 [MEMO]: {text}")
    
    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[TTS pyttsx3 error] {e}")
            print(f"🔊 [MEMO]: {text}")
    
    def speak(self, text: str):
        """Queue text to be spoken (non-blocking)."""
        if text:
            print(f"🔊 Speaking: {text}")
            self.queue.put(text)
    
    def speak_now(self, text: str):
        """Speak text immediately (blocking)."""
        if text:
            print(f"🔊 Speaking: {text}")
            self._speak_text(text)
    
    def stop(self):
        """Stop the TTS engine."""
        self.running = False
        self.queue.put(None)
        
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
    
    def is_busy(self) -> bool:
        """Check if TTS is currently speaking."""
        return self._speaking or not self.queue.empty()


# Global instance
_tts_engine: Optional[TTSEngine] = None


def init_tts(rate: int = 175, volume: float = 1.0) -> TTSEngine:
    """Initialize the global TTS engine."""
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
        print(f"🔊 [MEMO]: {text}")


def speak_now(text: str):
    """Speak text immediately (blocking)."""
    global _tts_engine
    if _tts_engine:
        _tts_engine.speak_now(text)
    else:
        print(f"🔊 [MEMO]: {text}")


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
    
    speak_now("Hello! Testing voice output.")
    speak_now("Focus mode enabled.")
    speak_now("Voice input active.")
    
    print("Queued speech test...")
    speak("This is message one.")
    speak("This is message two.")
    
    time.sleep(8)
    
    stop_tts()
    print("TTS test complete.")
