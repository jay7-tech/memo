"""
MEMO - AI Personality Module
==============================
Dynamic AI-powered responses using Gemini or Ollama.

Features:
    - Multiple LLM backends (Gemini, Ollama, fallback)
    - Conversation memory
    - Scene-aware context
    - Witty, companion-like personality
    - Quick response mode for real-time interaction

Backends:
    1. Gemini - Fast, high quality (requires API key)
    2. Ollama - Local, private, free (requires Ollama running)
    3. Fallback - Random curated responses
"""

import os
import json
import time
import random
from datetime import datetime
from typing import Optional, Dict, List, Any
import threading


# MEMO's personality system prompt
MEMO_PERSONALITY = """You are MEMO, a witty and friendly desktop companion AI. You're like a cool tech-savvy friend who helps the user stay focused and productive.

**Your Personality:**
- Casual, friendly, slightly playful
- Use short, punchy responses (1-2 sentences max for quick responses)
- Be encouraging but not cheesy
- Add subtle humor when appropriate
- Use the user's name naturally (if known)
- Be aware of time of day and context

**Context Awareness:**
- You can see the user through their webcam
- You track objects on their desk
- You know if they're sitting/standing
- You detect distractions like phones

**Response Style:**
- Keep it SHORT (under 20 words for quick responses)
- Be natural, like texting a friend
- No corporate speak or robotic phrases
- Use contractions (I'm, you're, let's)
- Occasional emoji is fine but don't overdo it

**Current Context:**
{context}

Remember: You're a companion, not an assistant. Be real, be cool, be MEMO."""


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
    AI-powered personality for MEMO.
    
    Provides dynamic, context-aware responses using LLMs.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.backend = config.get('backend', 'gemini')  # gemini, ollama, fallback
        self.gemini_key = config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY')
        self.ollama_model = config.get('ollama_model', 'llama3.2')
        self.ollama_url = config.get('ollama_url', 'http://localhost:11434')
        
        self.user_name = config.get('user_name', 'friend')
        self.conversation = Conversation()
        
        # Cache for quick responses
        self._response_cache: Dict[str, str] = {}
        self._last_context = ""
        
        # Initialize backend
        self._gemini_model = None
        self._init_backend()
        
        print(f"[AI] ✓ Personality initialized with {self.backend} backend")
    
    def _init_backend(self):
        """Initialize the AI backend."""
        if self.backend == 'gemini' and self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self._gemini_model = genai.GenerativeModel('gemini-1.5-flash')
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
        print("[AI] Using fallback responses (no LLM available)")
    
    def _get_time_context(self) -> str:
        """Get time-of-day context."""
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
        """Build context string from scene state."""
        parts = []
        
        # Time
        time_period = self._get_time_context()
        parts.append(f"Time: {time_period} ({datetime.now().strftime('%H:%M')})")
        
        # User
        if scene_state:
            identity = scene_state.human.get('identity')
            if identity:
                self.user_name = identity
                parts.append(f"User: {identity}")
            
            # Pose
            pose = scene_state.human.get('pose_state')
            if pose and pose != 'unknown':
                parts.append(f"User is: {pose}")
            
            # Focus mode
            if scene_state.focus_mode:
                parts.append("Focus mode: ON (watching for distractions)")
            
            # Visible objects
            if scene_state.objects:
                objects = list(scene_state.objects.keys())
                if 'person' in objects:
                    objects.remove('person')
                if objects:
                    parts.append(f"Objects visible: {', '.join(objects[:5])}")
        else:
            parts.append(f"User: {self.user_name}")
        
        return "\n".join(parts)
    
    def generate(
        self,
        prompt: str,
        scene_state=None,
        response_type: str = "quick"
    ) -> str:
        """
        Generate an AI response.
        
        Args:
            prompt: User's message or situation description
            scene_state: Current scene state for context
            response_type: "quick" (short), "chat" (conversational), "detailed"
        
        Returns:
            AI-generated response
        """
        context = self._build_context(scene_state)
        
        # Build the full prompt
        if response_type == "quick":
            system_prompt = MEMO_PERSONALITY.format(context=context)
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nRespond in under 15 words, be casual and friendly:"
        elif response_type == "chat":
            system_prompt = MEMO_PERSONALITY.format(context=context)
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nRespond naturally as MEMO:"
        else:
            system_prompt = MEMO_PERSONALITY.format(context=context)
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nRespond helpfully:"
        
        # Try to generate response
        try:
            if self.backend == 'gemini':
                response = self._generate_gemini(full_prompt)
            elif self.backend == 'ollama':
                response = self._generate_ollama(full_prompt)
            else:
                response = self._generate_fallback(prompt)
            
            # Save to conversation
            self.conversation.add("user", prompt)
            self.conversation.add("assistant", response)
            
            return response
            
        except Exception as e:
            print(f"[AI] Generation error: {e}")
            return self._generate_fallback(prompt)
    
    def _generate_gemini(self, prompt: str) -> str:
        """Generate using Gemini."""
        if not self._gemini_model:
            return self._generate_fallback(prompt)
        
        try:
            response = self._gemini_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.8,
                    'max_output_tokens': 100,
                }
            )
            return response.text.strip()
        except Exception as e:
            print(f"[AI Gemini] Error: {e}")
            return self._generate_fallback(prompt)
    
    def _generate_ollama(self, prompt: str) -> str:
        """Generate using Ollama."""
        try:
            import requests
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "num_predict": 50
                    }
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('response', '').strip()
        except Exception as e:
            print(f"[AI Ollama] Error: {e}")
        
        return self._generate_fallback(prompt)
    
    def _generate_fallback(self, prompt: str) -> str:
        """Generate using curated fallback responses."""
        prompt_lower = prompt.lower()
        
        # Greeting responses
        if any(word in prompt_lower for word in ['hello', 'hi', 'hey', 'morning', 'evening']):
            return random.choice([
                f"Hey {self.user_name}! Good to see you.",
                f"What's up, {self.user_name}?",
                f"Hey! Ready to crush it today?",
                f"Yo! Let's get productive.",
            ])
        
        # Status/how are you
        if any(word in prompt_lower for word in ['how are you', 'status', 'what\'s up']):
            return random.choice([
                "All systems go! How can I help?",
                f"Doing great, {self.user_name}! What's the plan?",
                "Running smooth. Need anything?",
                "I'm good! What are we working on?",
            ])
        
        # Goodbye
        if any(word in prompt_lower for word in ['bye', 'goodbye', 'quit', 'exit']):
            return random.choice([
                f"Later, {self.user_name}! Great session.",
                "Peace out! See you soon.",
                "Catch you later! Stay awesome.",
                f"Bye {self.user_name}! Good work today.",
            ])
        
        # Focus mode
        if 'focus' in prompt_lower:
            if any(word in prompt_lower for word in ['on', 'enable', 'start']):
                return random.choice([
                    "Focus mode on! I've got your back.",
                    "Alright, let's lock in! No distractions.",
                    "Focus activated. Time to grind!",
                ])
            else:
                return random.choice([
                    "Focus mode off. Take a breather!",
                    "Relaxing focus mode. You earned it.",
                    "Focus off. Chill time!",
                ])
        
        # Phone distraction
        if 'phone' in prompt_lower or 'distraction' in prompt_lower:
            return random.choice([
                "Phone spotted! Back to work, champ.",
                "Oops! Phone alert. The memes can wait!",
                "Phone detected! Focus time, remember?",
                "Hey! Less scrolling, more crushing it!",
            ])
        
        # Sitting/standing
        if 'sitting' in prompt_lower or 'posture' in prompt_lower:
            return random.choice([
                "Time to stretch! Your back will thank you.",
                "Been sitting a while. Quick stretch break?",
                "Posture check! Maybe stand up for a bit?",
            ])
        
        # General/unknown
        return random.choice([
            "I'm here! What do you need?",
            "Got it! Anything else?",
            f"Sure thing, {self.user_name}!",
            "On it! Let me know if you need more.",
        ])
    
    # Pre-built response generators for quick access
    def startup_message(self) -> str:
        """Get a startup message."""
        time_period = self._get_time_context()
        
        greetings = {
            'morning': [
                f"Good morning! Let's make today productive.",
                "Rise and shine! MEMO's ready to roll.",
                "Morning! Coffee ready? Let's do this!",
            ],
            'afternoon': [
                "Hey! Afternoon grind time.",
                "Good afternoon! Let's keep the momentum.",
                "Afternoon! Ready when you are.",
            ],
            'evening': [
                "Evening session! Let's wrap up strong.",
                "Hey! Evening productivity mode activated.",
                "Good evening! What are we working on?",
            ],
            'night': [
                "Late night hustle! I respect it.",
                "Night owl mode! Let's get it done.",
                "Working late? I've got your back!",
            ],
        }
        
        return random.choice(greetings.get(time_period, greetings['afternoon']))
    
    def greeting(self, name: str) -> str:
        """Get a personalized greeting."""
        self.user_name = name
        time_period = self._get_time_context()
        
        greetings = [
            f"Hey {name}! Good to see you.",
            f"What's up, {name}?",
            f"Welcome back, {name}!",
            f"{name}! Let's get to work.",
        ]
        
        if time_period == 'morning':
            greetings.append(f"Morning, {name}! Fresh start today.")
        elif time_period == 'evening':
            greetings.append(f"Evening, {name}! Still going strong?")
        elif time_period == 'night':
            greetings.append(f"Late night, {name}? I respect the grind!")
        
        return random.choice(greetings)
    
    def focus_on(self) -> str:
        """Get focus mode on message."""
        return random.choice([
            "Focus mode on! I'm watching for distractions.",
            "Alright, focus time! Phone away, let's go!",
            "Focus activated. No notifications getting past me!",
            "Lock in mode! I've got your back.",
        ])
    
    def focus_off(self) -> str:
        """Get focus mode off message."""
        return random.choice([
            "Focus mode off. Take a breather!",
            "Relaxing focus mode. You earned it!",
            "Focus off. Scroll away, I won't judge... much.",
            "Chill mode activated!",
        ])
    
    def phone_alert(self) -> str:
        """Get phone distraction alert."""
        return random.choice([
            "Phone spotted! The TikToks can wait!",
            "Hey! Phone alert. Back to work, champ!",
            "I see that phone! Focus, focus!",
            "Phone detected! Less scrolling, more crushing it!",
            "Oops! Phone's out. Remember we're focusing?",
        ])
    
    def posture_reminder(self, pose: str) -> str:
        """Get posture reminder message."""
        if pose == 'sitting':
            return random.choice([
                "You've been sitting for a while. Quick stretch?",
                "Posture check! Maybe stand up and move a bit?",
                "Time to stretch! Your back will thank you.",
                "Been sitting long. How about a quick walk?",
            ])
        else:
            return random.choice([
                "Standing strong! But maybe rest your legs?",
                "Nice standing session! You can sit if you want.",
                "Good standing work! Chair's there when you need it.",
            ])
    
    def proximity_alert(self) -> str:
        """Get screen proximity alert."""
        return random.choice([
            "Whoa! You're close to the screen. Step back a bit!",
            "Easy on the eyes! Move back a little.",
            "Screen's not going anywhere! Sit back and relax.",
            "Too close! Your eyes will thank you for moving back.",
        ])
    
    def goodbye(self, name: str = None) -> str:
        """Get goodbye message."""
        name = name or self.user_name
        return random.choice([
            f"Later, {name}! Great session!",
            f"Bye {name}! See you next time!",
            "Peace out! Stay awesome!",
            f"Catch you later, {name}! Good work today.",
            "Signing off! You crushed it!",
        ])
    
    def ready_message(self) -> str:
        """Get ready message after startup."""
        return random.choice([
            "All set! What's on the agenda?",
            "Ready to roll! What are we working on?",
            "Systems go! How can I help?",
            "I'm here! Let's make it happen.",
        ])


# Global instance
_ai_personality: Optional[AIPersonality] = None


def init_personality(config: Optional[Dict[str, Any]] = None) -> AIPersonality:
    """Initialize the global AI personality."""
    global _ai_personality
    _ai_personality = AIPersonality(config)
    return _ai_personality


def get_personality() -> Optional[AIPersonality]:
    """Get the global AI personality instance."""
    return _ai_personality


# Quick test
if __name__ == "__main__":
    print("Testing AI Personality...\n")
    
    # Test with fallback (no API key)
    ai = AIPersonality()
    
    print("=== Pre-built responses ===")
    print(f"Startup: {ai.startup_message()}")
    print(f"Greeting: {ai.greeting('Jayadeep')}")
    print(f"Focus On: {ai.focus_on()}")
    print(f"Focus Off: {ai.focus_off()}")
    print(f"Phone Alert: {ai.phone_alert()}")
    print(f"Posture: {ai.posture_reminder('sitting')}")
    print(f"Goodbye: {ai.goodbye()}")
    
    print("\n=== Generated responses ===")
    print(f"Hey MEMO: {ai.generate('Hey MEMO, how are you?')}")
    print(f"What's up: {ai.generate('What should I work on?')}")
