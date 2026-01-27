"""
MEMO - Text-to-Speech Module
=============================
Improved TTS with multiple backends and better reliability.
"""

import queue
import threading
import subprocess
import sys

# TTS Backend selection
TTS_BACKEND = None  # Will be set during init


class TTSEngine:
    """
    Text-to-Speech engine with multiple backend support.
    
    Backends (in order of preference):
    1. pyttsx3 - Fast, offline, cross-platform
    2. PowerShell SAPI - Windows built-in (fallback)
    3. Print-only - Just prints to console (last resort)
    """
    
    def __init__(self):
        self.queue = queue.Queue()
        self.running = True
        self.backend_type = self._detect_backend()
        self.worker_thread = None
        self._lock = threading.Lock()  # Lock for thread-safe speech
        
    def _detect_backend(self):
        """Detect the best available TTS backend."""
        
        # Try pyttsx3 first (best option)
        try:
            import pyttsx3
            # Just test if we can create an engine
            test_engine = pyttsx3.init()
            test_engine.stop()
            print("[TTS] Using pyttsx3 engine")
            return 'pyttsx3'
        except Exception as e:
            print(f"[TTS] pyttsx3 not available: {e}")
        
        # Fallback to PowerShell SAPI
        if sys.platform == 'win32':
            print("[TTS] Using PowerShell SAPI engine")
            return 'powershell'
        
        # Last resort - just print
        print("[TTS] No TTS engine available, using print-only mode")
        return 'print'
    
    def _create_pyttsx3_engine(self):
        """Create a fresh pyttsx3 engine instance for each speech request."""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)  # Slightly faster
        engine.setProperty('volume', 1.0)
        
        # Get available voices
        voices = engine.getProperty('voices')
        # Try to use a more natural voice if available
        for voice in voices:
            if 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        return engine
    
    def start(self):
        """Start the TTS worker thread."""
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
    
    def _speak_sync(self, text):
        """Speak text synchronously using the selected backend."""
        with self._lock:  # Ensure thread-safe access
            if self.backend_type == 'pyttsx3':
                try:
                    # Create a fresh engine for each request to avoid "run loop already started" error
                    engine = self._create_pyttsx3_engine()
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()  # Clean up
                except Exception as e:
                    print(f"[TTS pyttsx3 error] {e}")
                    # Fallback to PowerShell
                    self._speak_powershell(text)
                    
            elif self.backend_type == 'powershell':
                self._speak_powershell(text)
                
            else:  # print mode
                print(f"🔊 [MEMO says]: {text}")
    
    def _speak_powershell(self, text):
        """Speak using Windows PowerShell SAPI."""
        try:
            safe_text = text.replace("'", "''").replace('"', '`"')
            cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}');"
            
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                check=False,
                capture_output=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            print(f"[TTS] Speech timeout for: {text[:30]}...")
        except Exception as e:
            print(f"[TTS PowerShell error] {e}")
            print(f"🔊 [MEMO says]: {text}")
    
    def speak(self, text):
        """
        Queue text to be spoken (non-blocking).
        
        Args:
            text: The text to speak
        """
        if text:
            print(f"🔊 Speaking: {text}")  # Always show what's being said
            self.queue.put(text)
    
    def speak_now(self, text):
        """
        Speak text immediately (blocking).
        Use for important announcements.
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


# Global instance
_tts_engine = None


def init_tts():
    """Initialize the global TTS engine."""
    global _tts_engine
    _tts_engine = TTSEngine()
    _tts_engine.start()
    return _tts_engine


def speak(text):
    """Queue text to be spoken."""
    global _tts_engine
    if _tts_engine:
        _tts_engine.speak(text)
    else:
        print(f"🔊 [MEMO says]: {text}")


def speak_now(text):
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


# Test the TTS engine
if __name__ == "__main__":
    print("Testing TTS Engine...")
    engine = init_tts()
    
    speak("Hello! I am MEMO, your desktop companion.")
    speak("Testing text to speech functionality.")
    speak_now("This is a blocking speech test.")
    
    import time
    time.sleep(5)  # Wait for queued speech
    
    stop_tts()
    print("TTS test complete.")
