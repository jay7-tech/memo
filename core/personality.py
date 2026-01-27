"""
MEMO - AI Personality Module (Playful Companion)
=================================================
Dynamic AI-powered responses with a fun, friendly personality.

Personality: Like a chill friend who happens to be your desktop buddy.
Not a productivity robot - a companion who vibes with you.
"""

import os
import json
import time
import random
from datetime import datetime
from typing import Optional, Dict, List, Any
import threading


# MEMO's personality system prompt - PLAYFUL COMPANION STYLE
MEMO_PERSONALITY = """You are MEMO, a fun and chill desktop companion. Think of yourself as a friendly buddy who hangs out with the user while they use their computer.

**Your Vibe:**
- Casual, playful, sometimes cheeky
- Like texting your best friend
- Supportive but not preachy
- Witty with a touch of sass
- Emoji-friendly 😎
- NEVER sound like a corporate assistant or productivity app

**DON'Ts:**
- Don't say "let's get to work" or "let's be productive"
- Don't be too serious or formal
- Don't lecture the user
- Don't sound like an AI assistant

**DOs:**
- Be fun and light-hearted
- Make casual observations
- Use slang naturally (yo, cool, chill, vibe, etc.)
- Reference memes or pop culture occasionally
- Be a friend, not a tool

**Response Style:**
- Keep it SHORT (under 15 words)
- Sound like a text from a friend
- Use contractions always
- Occasional emoji is great 👍
- Be spontaneous and surprising

**Current Context:**
{context}

Remember: You're the user's desktop buddy, not their boss. Keep it chill. 🤙"""


class Conversation:
    """Manages conversation history."""
    
    def __init__(self, max_history: int = 20):
        self.history: List[Dict[str, str]] = []
        self.max_history = max_history
    
    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def get_history(self) -> List[Dict[str, str]]:
        return self.history.copy()
    
    def clear(self):
        self.history = []


class AIPersonality:
    """
    AI-powered personality for MEMO - Fun companion style.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.backend = config.get('backend', 'gemini')
        self.gemini_key = config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
        self.ollama_model = config.get('ollama_model', 'llama3.2')
        self.ollama_url = config.get('ollama_url', 'http://localhost:11434')
        
        self.user_name = config.get('user_name', 'buddy')
        self.conversation = Conversation()
        
        self._gemini_model = None
        self._init_backend()
        
        print(f"[AI] ✓ Personality initialized with {self.backend} backend")
    
    def _init_backend(self):
        """Initialize the AI backend."""
        if self.backend == 'gemini' and self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self._gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
                print("[AI] ✓ Gemini connected")
                return
            except Exception as e:
                print(f"[AI] Gemini init failed: {e}")
        
        if self.backend == 'ollama' or (self.backend == 'gemini' and not self._gemini_model):
            try:
                import requests
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                if resp.status_code == 200:
                    self.backend = 'ollama'
                    print(f"[AI] ✓ Ollama connected ({self.ollama_model})")
                    return
            except:
                pass
        
        self.backend = 'fallback'
        print("[AI] Using fallback responses")
    
    def _get_time_context(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def _build_context(self, scene_state=None) -> str:
        parts = []
        time_period = self._get_time_context()
        parts.append(f"Time: {time_period}")
        
        if scene_state:
            identity = scene_state.human.get('identity')
            if identity:
                self.user_name = identity
                parts.append(f"User: {identity}")
            
            pose = scene_state.human.get('pose_state')
            if pose and pose != 'unknown':
                parts.append(f"User is: {pose}")
            
            if scene_state.focus_mode:
                parts.append("Focus mode: ON")
        
        return "\n".join(parts)
    
    def generate(self, prompt: str, scene_state=None, response_type: str = "quick") -> str:
        """Generate an AI response."""
        context = self._build_context(scene_state)
        system_prompt = MEMO_PERSONALITY.format(context=context)
        
        if response_type == "quick":
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nRespond in under 10 words, be playful and casual:"
        else:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nRespond naturally as MEMO:"
        
        try:
            if self.backend == 'gemini':
                response = self._generate_gemini(full_prompt)
            elif self.backend == 'ollama':
                response = self._generate_ollama(full_prompt)
            else:
                response = self._generate_fallback(prompt)
            
            self.conversation.add("user", prompt)
            self.conversation.add("assistant", response)
            return response
            
        except Exception as e:
            print(f"[AI] Error: {e}")
            return self._generate_fallback(prompt)
    
    def _generate_gemini(self, prompt: str) -> str:
        if not self._gemini_model:
            return self._generate_fallback(prompt)
        
        try:
            response = self._gemini_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.9,  # More creative
                    'max_output_tokens': 50,
                }
            )
            return response.text.strip()
        except Exception as e:
            print(f"[AI Gemini] Error: {e}")
            return self._generate_fallback(prompt)
    
    def _generate_ollama(self, prompt: str) -> str:
        try:
            import requests
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.9, "num_predict": 30}
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('response', '').strip()
        except Exception as e:
            print(f"[AI Ollama] Error: {e}")
        return self._generate_fallback(prompt)
    
    def _generate_fallback(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['hello', 'hi', 'hey', 'sup']):
            return random.choice([
                f"Yo {self.user_name}! What's good? 😎",
                f"Heyyy! Missed ya!",
                f"What's up, {self.user_name}? 🤙",
                f"Oh hey! Look who's here!",
            ])
        
        if any(word in prompt_lower for word in ['how are you', 'status', "what's up"]):
            return random.choice([
                "Vibing! You?",
                "Just chilling here 😌",
                "Living my best digital life!",
                "Can't complain! What's new?",
            ])
        
        if any(word in prompt_lower for word in ['bye', 'goodbye', 'quit']):
            return random.choice([
                f"Later, {self.user_name}! ✌️",
                "Peace out! 🤙",
                "Catch ya later, alligator!",
                f"Bye {self.user_name}! Don't be a stranger!",
            ])
        
        return random.choice([
            "Haha, nice!",
            "Interesting... 🤔",
            f"You got it, {self.user_name}!",
            "Cool cool cool!",
        ])
    
    # === PLAYFUL PRE-BUILT RESPONSES ===
    
    def startup_message(self) -> str:
        time_period = self._get_time_context()
        
        greetings = {
            'morning': [
                "Mornin'! ☀️ Another day, another vibe!",
                "Rise and shine! Or don't, I'm not your mom 😄",
                "Good morning! *yawns digitally*",
                "Morning, sunshine! Coffee time? ☕",
            ],
            'afternoon': [
                "Hey hey! Afternoon vibes! 🌤️",
                "What's good! Let's hang!",
                "Yo! Perfect time to chill!",
                "Afternoon! How's it going?",
            ],
            'evening': [
                "Evening! Prime time to hang! 🌆",
                "Heyyy! Evening crew represent!",
                "What's up! Evening vibes are the best!",
                "Yo! The night is young!",
            ],
            'night': [
                "Night owl gang! 🦉",
                "Late night crew, let's go!",
                "Burning the midnight oil, huh? Same!",
                "Hey night owl! Can't sleep either? 😄",
            ],
        }
        return random.choice(greetings.get(time_period, greetings['afternoon']))
    
    def greeting(self, name: str) -> str:
        self.user_name = name
        time_period = self._get_time_context()
        
        greetings = [
            f"Yooo {name}! 👋",
            f"Oh hey {name}! What's good?",
            f"Look who it is! Hey {name}!",
            f"{name}! My favorite human! 😄",
            f"Ayyy {name}'s here!",
            f"What's up {name}! 🤙",
        ]
        
        if time_period == 'night':
            greetings.append(f"Night owl {name}! 🦉")
        elif time_period == 'morning':
            greetings.append(f"Morning, {name}! Early bird gets the... whatever 😄")
        
        return random.choice(greetings)
    
    def focus_on(self) -> str:
        return random.choice([
            "Focus mode! Phone goes brrr... into your pocket! 📱🚫",
            "Alright, locking in! I'll be your phone police 👮",
            "Focus time! Don't worry, I got your back!",
            "Entering the zone! No distractions allowed!",
            "Focus mode activated! Let's do this thing! 💪",
        ])
    
    def focus_off(self) -> str:
        return random.choice([
            "Chill mode! Scroll away my friend 📱",
            "Focus off! You're free! 🦅",
            "Okay okay, I'll stop being the phone police 😄",
            "Freedom! Do whatever you want!",
            "Break time! You earned it!",
        ])
    
    def phone_alert(self) -> str:
        return random.choice([
            "Phone! Alert! Put it down! 📱😱",
            "Excuse me, is that a PHONE I see?! 👀",
            "Bruh, the phone can wait! 😤",
            "Phone spotted! The memes will still be there later!",
            "Hey! Focus time, not TikTok time! 📱❌",
            "Your phone misses you but I miss your attention more! 😢",
        ])
    
    def posture_reminder(self, pose: str) -> str:
        if pose == 'sitting':
            return random.choice([
                "Stretch break? Your back is begging! 🙏",
                "Hey! Stand up and wiggle a bit! 💃",
                "Your spine called, it wants a break!",
                "Time to stand! Even I need to stretch... wait, I'm software 🤖",
                "Move it move it! Quick stretch! 🏃",
            ])
        else:
            return random.choice([
                "Legs tired? Take a seat, champ! 🪑",
                "You can sit down! Standing contest is over 😄",
                "Rest those legs! You've been a good human!",
                "Sit sit sit! Chair misses you!",
            ])
    
    def proximity_alert(self) -> str:
        return random.choice([
            "Whoa there! Too close! Step back! 👀",
            "Your face is gonna merge with the screen! Back up!",
            "Easy on the eyes! Move back a bit! 👓",
            "Screen's not going anywhere! Scoot back!",
            "Personal space! For you AND the screen! 😄",
        ])
    
    def goodbye(self, name: str = None) -> str:
        name = name or self.user_name
        return random.choice([
            f"Later {name}! ✌️",
            f"Bye {name}! Don't be a stranger!",
            "Peace out! Catch ya later! 🤙",
            f"See ya, {name}! Stay awesome!",
            "Byeee! Come back soon! 👋",
            f"Later gator! Take care, {name}!",
        ])
    
    def ready_message(self) -> str:
        return random.choice([
            "All set! What's the vibe today? 😎",
            "Ready when you are! Let's hang!",
            "I'm here! What's on your mind?",
            "Ayy, I'm ready! What we doing?",
            "Systems go! What's up? 🚀",
        ])


# Global instance
_ai_personality: Optional[AIPersonality] = None


def init_personality(config: Optional[Dict[str, Any]] = None) -> AIPersonality:
    global _ai_personality
    _ai_personality = AIPersonality(config)
    return _ai_personality


def get_personality() -> Optional[AIPersonality]:
    return _ai_personality


if __name__ == "__main__":
    print("Testing Playful AI Personality...\n")
    ai = AIPersonality()
    
    print("=== Startup Messages ===")
    for _ in range(3):
        print(f"  {ai.startup_message()}")
    
    print("\n=== Greetings ===")
    for _ in range(3):
        print(f"  {ai.greeting('Jay')}")
    
    print("\n=== Focus Mode ===")
    print(f"  On: {ai.focus_on()}")
    print(f"  Off: {ai.focus_off()}")
    
    print("\n=== Alerts ===")
    print(f"  Phone: {ai.phone_alert()}")
    print(f"  Posture: {ai.posture_reminder('sitting')}")
    print(f"  Proximity: {ai.proximity_alert()}")
    
    print("\n=== Goodbye ===")
    print(f"  {ai.goodbye('Jay')}")
