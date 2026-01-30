"""
MEMO - core/features.py
Feature Managers (Vibe DJ, Scene Narrator, etc.)
"""

import time
import webbrowser
import threading
import random
from typing import Optional, Dict, Any

class VibeManager:
    """
    Vibe DJ: Manages background music based on user energy levels.
    """
    
    def __init__(self):
        self.current_vibe = "none"
        self.last_switch_time = 0
        self.cooldown = 15.0 # Seconds between vibe checks
        self.browser_open = False
        
        # Youtube Music Playlists (Ad-free / Ambient mostly)
        self.playlists = {
            'chill': [
                "https://www.youtube.com/watch?v=jfKfPfyJRdk", # Lofi Girl
                "https://www.youtube.com/watch?v=5qap5aO4i9A", # Lofi Hip Hop
                "https://www.youtube.com/watch?v=DWcJFNfaw9c"  # Ambient Reading
            ],
            'energy': [
                "https://www.youtube.com/watch?v=S374IadRjX8", # Upbeat Pop
                "https://www.youtube.com/watch?v=fKopiaCJKWk", # Coding Mode
                "https://www.youtube.com/watch?v=5yx6BWlEVcY"  # Chillhop
            ]
        }
    
    def check_vibe(self, scene_state) -> Optional[str]:
        """
        Determines the current vibe based on user pose.
        Returns 'chill', 'energy', or None (no change).
        """
        timestamp = time.time()
        
        # Debounce
        if timestamp - self.last_switch_time < self.cooldown:
            return None
            
        if not scene_state.human['present']:
            return None
            
        pose = scene_state.human.get('pose_state', 'unknown')
        
        # Vibe Logic
        new_vibe = None
        if pose == 'sitting':
            new_vibe = 'chill'
        elif pose == 'standing' or pose == 'walking':
            new_vibe = 'energy'
            
        # Only trigger if vibe CHANGED
        if new_vibe and new_vibe != self.current_vibe:
            self.current_vibe = new_vibe
            self.last_switch_time = timestamp
            return new_vibe
            
        return None

    def play_music(self, vibe: str):
        """Opens a random playlist for the given vibe."""
        if vibe not in self.playlists:
            return
            
        url = random.choice(self.playlists[vibe])
        
        # On Pi, opening a browser might be heavy, but let's try 'xdg-open' equivalent via python
        try:
            print(f"[VibeDJ] 🎵 Switching to {vibe.upper()} mode: {url}")
            webbrowser.open(url) 
            self.browser_open = True
        except Exception as e:
            print(f"[VibeDJ] Error opening music: {e}")

    def stop_music(self):
        """
        Stops music (Hard to do generically with webbrowser, 
        but we can reset state).
        """
        self.current_vibe = "none"
        # Note: We can't easily close the browser tab from Python without Selenium/Puppeteer.
        # For now, we just stop tracking.
