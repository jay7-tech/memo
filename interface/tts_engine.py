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
        
        # Persistent engines
        self._pyttsx3_engine = None
        
        # Detect platform and backend
        self._backend = self._detect_backend()
        print(f"[TTS] ✓ Using {self._backend} engine")
    
    def _detect_backend(self) -> str:
        """Detect the best TTS backend."""
        if sys.platform == 'win32':
            try:
                import comtypes.client
                return 'sapi_direct'
            except ImportError:
                return 'sapi'  # Fallback to VBS method
                
        # Check for piper (High quality for Linux/Pi)
        if os.path.exists("./piper/piper") or os.path.exists("/usr/local/bin/piper"):
            return 'piper'
            
        # Check for espeak on Linux/Pi
        try:
            result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                return 'espeak'
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
        # Initialize COM for this thread
        try:
            import comtypes
            comtypes.CoInitialize()
        except:
            pass
            
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
                elif self._backend == 'piper':
                    self._speak_piper(text)
                elif self._backend == 'sapi_direct':
                    self._speak_sapi_direct(text)
                else:
                    print(f"🔊 [MEMO]: {text}")
            finally:
                self._speaking = False
    
    def _clean_text(self, text: str) -> str:
        """Clean text for speech by removing hashtags and emojis for the engine."""
        # Convert to string
        text = str(text)

        # Strip prefixes like "MEMO: " or "SYSTEM: "
        import re
        text = re.sub(r'^(MEMO|SYSTEM):\s*', '', text, flags=re.IGNORECASE)
        
        # Strip internal labels like "TTS:"
        text = text.replace("TTS:", "").strip()
        
        # Strip emojis for the voice engine
        clean = re.sub(r'[^\x00-\x7F]+', ' ', text)
        
        # Remove hashtags
        clean = re.sub(r'#\w+', '', clean)
        
        # Remove multiple spaces
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        if clean and clean[-1] not in '.!?':
            clean += '.'
        return clean

    def _speak_sapi(self, text: str):
        """Speak using Windows SAPI with natural voice and text cleaning."""
        try:
            # Clean text JUST for the engine
            speech_text = self._clean_text(text)
            if not speech_text:
                return

            # Escape quotes for VBS
            safe_text = speech_text.replace('"', '""').replace("'", "''")
            
            # VBS script with voice selection and rate control
            vbs_content = f'''
Set speech = CreateObject("SAPI.SpVoice")

' Try to find a natural-sounding voice
For Each voice In speech.GetVoices
    If InStr(voice.GetDescription, "Zira") > 0 Then
        Set speech.Voice = voice
        Exit For
    ElseIf InStr(voice.GetDescription, "Eva") > 0 Then
        Set speech.Voice = voice
        Exit For
    ElseIf InStr(voice.GetDescription, "David") > 0 Then
        Set speech.Voice = voice
    End If
Next

' Rate settings for more natural flow
speech.Rate = 1 
speech.Volume = {int(self.volume * 100)}

' Natural phrasing: Add small pauses at commas/periods
text = "{safe_text}"
text = Replace(text, ",", ", ")
text = Replace(text, ".", ". ")

speech.Speak text
'''
            # Write temp VBS file
            vbs_path = os.path.join(os.environ.get('TEMP', '.'), 'memo_speak.vbs')
            with open(vbs_path, 'w', encoding='utf-8') as f:
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

    def _speak_piper(self, text: str):
        """Speak using Piper TTS (High Quality for Pi)."""
        try:
            # Paths
            piper_bin = "./piper/piper" if os.path.exists("./piper/piper") else "piper"
            model_path = "./piper/models/en_US-lessac-medium.onnx"
            
            if not os.path.exists(model_path) and piper_bin == "./piper/piper":
                # Fallback to espeak if model missing
                print("[TTS] Piper model missing, falling back to espeak")
                self._speak_espeak(text)
                return

            # Construct command: echo "text" | piper ... | aplay
            # Clean text for shell
            safe_text = text.replace('"', '\\"')
            
            # Determine audio player: try 'paplay' (PulseAudio) first, then 'aplay' (ALSA)
            # PulseAudio is better for desktop environments; ALSA for headless.
            
            # TRY 1: PulseAudio (paplay)
            # This is preferred on Raspberry Pi Desktop as it handles mixing and device selection automatically.
            try:
                cmd_pulse = f'echo "{safe_text}" | {piper_bin} --model {model_path} --output_raw | paplay --raw --format=s16le --rate=22050 --channels=1'
                subprocess.run(cmd_pulse, shell=True, timeout=10, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return # If successful, return
            except:
                pass # Fallback to aplay
                
            # TRY 2: ALSA (aplay) - Fallback
            cmd_alsa = f'echo "{safe_text}" | {piper_bin} --model {model_path} --output_raw | aplay -r 22050 -f S16_LE -t raw -'
            subprocess.run(cmd_alsa, shell=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except Exception as e:
            print(f"[TTS Piper error] {e}")
            self._speak_espeak(text)
    
    def _speak_sapi_direct(self, text: str):
        """Speak using direct SAPI COM interface (Reliable & Fast)."""
        try:
            import comtypes.client
            
            # Initialize COM object (Thread-local)
            if not hasattr(self, '_sapi_speaker'):
                print("[TTS] Initializing SAPI COM...")
                self._sapi_speaker = comtypes.client.CreateObject("SAPI.SpVoice")
                
                # Select Zira voice
                voices = self._sapi_speaker.GetVoices()
                for i in range(voices.Count):
                    voice = voices.Item(i)
                    if "Zira" in voice.GetDescription() or "Eva" in voice.GetDescription():
                        self._sapi_speaker.Voice = voice
                        break
                        
                self._sapi_speaker.Rate = 1  # Moderate speed
                self._sapi_speaker.Volume = 100
                
            # Clean text
            speech_text = self._clean_text(text)
            if not speech_text:
                return
            
            # Speak (SVSFlagsAsync = 1) -> Actually, we want synchronous here 
            # because we are in a background worker thread.
            self._sapi_speaker.Speak(speech_text)
            
        except Exception as e:
            print(f"[TTS SAPI Direct error] {e}")
            # Fallback
            self._speak_sapi(text)
    
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
