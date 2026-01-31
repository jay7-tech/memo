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


MEMO_PERSONALITY = """<SYSTEM>
You are MEMO.A  smart assistant robot
Answer in one short helpful sentence.
Think before answering.
Be natural and clear.
</SYSTEM>

Context:
{context}

Examples:

[User]: Tell me a fact
[MEMO]: Honey never spoils.

[User]: Tell me a joke
[MEMO]: Robots hate bugs in their code.

[User]: Who is Musk?
[MEMO]: Elon Musk is CEO of Tesla and SpaceX.

[User]: What is gravity?
[MEMO]: Gravity is the force that attracts objects toward each other.
"""


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
        self.ollama_model = config.get('ollama_model', 'phi3:mini')
        self.ollama_url = config.get('ollama_url', 'http://localhost:11434')
        
        self.user_name = config.get('user_name', 'buddy')
        self.conversation = Conversation()
        
        self._gemini_model = None
        self._gemini_client = None
        self._generate_lock = threading.Lock()
        self._init_backend()
        
        print(f"[AI] ✓ Personality initialized with {self.backend} backend")

    def detect_intent(self, q):
        q = q.lower()

        if any(x in q for x in ["time", "date", "day"]):
            return "datetime"

        if any(x in q for x in ["calculate", "+", "-", "*", "/"]):
            return "math"

        if "has teeth but cannot eat" in q:
            return "riddle"

        if q.startswith("who is") or q.startswith("what is"):
            return "fact"

        return "chat"

    def _init_backend(self):
        """Initialize the AI backend with a robust model search and fallback."""
        self._gemini_client = None
        self.active_model = 'gemini-1.5-flash' # Default
        
        # Try Gemini
        if self.backend == 'gemini' and self.gemini_key:
            print(f"[AI] Initializing Gemini...")
            
            # 1. Try New Google GenAI SDK
            try:
                from google import genai
                client = genai.Client(api_key=self.gemini_key)
                
                # Model candidates to try (Fastest first)
                candidates = [
                    'gemini-2.0-flash', 
                    'models/gemini-2.0-flash', 
                    'gemini-1.5-flash', 
                    'models/gemini-1.5-flash',
                    'gemini-1.5-pro'
                ]
                last_error = None
                
                for model_name in candidates:
                    try:
                        client.models.generate_content(model=model_name, contents='Start')
                        # If successful:
                        self._gemini_client = client
                        self.active_model = model_name
                        self.backend = 'gemini_new'
                        print(f"[AI] ✓ Brain: Gemini ({model_name}) connected.")
                        return
                    except Exception as e:
                        print(f"[AI] Debug: {model_name} failed: {e}")
                        last_error = e
                        continue
                
                print(f"[AI] New SDK installed but no working model found. Last error: {last_error}")
                
            except ImportError:
                print("[AI] Note: 'google-genai' package not installed. Skipping new SDK.")
            except Exception as e:
                print(f"[AI] New SDK Init failed: {e}")

            # 2. Try Legacy SDK
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                # Prioritize gemini-1.5-flash
                model = genai.GenerativeModel('gemini-1.5-flash')
                model.generate_content("Start")
                self._gemini_model = model
                self.backend = 'gemini'
                print("[AI] ✓ Brain: Gemini (Legacy SDK) connected.")
                return
            except Exception as e:
                print(f"[AI] Legacy SDK Init failed: {e}")
        
        # Fallback: Try Ollama
        try:
            import requests
            # Handle config inconsistencies (some users put full path in URL)
            base_url = self.ollama_url.replace("/api/generate", "").rstrip("/")
            
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                # Check if our configured model exists, or pick one from the list
                models = [m['name'] for m in resp.json().get('models', [])]
                if self.ollama_model in models:
                    self.backend = 'ollama'
                    print(f"[AI] ✓ Brain: Ollama ({self.ollama_model}) connected.")
                    return
                elif models:
                    self.ollama_model = models[0]
                    self.backend = 'ollama'
                    print(f"[AI] ✓ Brain: Ollama (using {self.ollama_model}) connected.")
                    return
        except:
            pass
        
        self.backend = 'fallback'
        print("[AI] Brain: Local Fallback activated (No LLM).")
    
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
        """Generate an AI response (Thread-safe and throttled)."""
        # PREVENTION: Don't overload the Pi with multiple LLM calls
        if not self._generate_lock.acquire(blocking=False):
            return "Just a sec, thinking..."
            
        try:
            # Local overrides for speed
            prompt_lower = prompt.lower().strip()
            
            # Intent Detection Integration
            intent = self.detect_intent(prompt_lower)
            
            if intent == "datetime":
                 return datetime.now().strftime("%A, %B %d %Y at %I:%M %p")
            
            if intent == "math":
                try:
                    # Basic safe eval for calculator
                    allowed = set("0123456789+-*/(). ")
                    if set(prompt.replace("calculate", "")).issubset(allowed):
                        return str(eval(prompt.replace("calculate","")))
                except:
                    pass # Fallback to LLM if math fails


            context = self._build_context(scene_state)
            system_prompt = MEMO_PERSONALITY.format(context=context)
            
            # Extract lightweight history (Last 6 turns)
            history_str = ""
            for h in self.conversation.get_history()[-6:]:
                role = "Q" if h['role'] == "user" else "A"
                history_str += f"{role}: {h['content']}\n"
            
            if self.backend == 'gemini_new' and self._gemini_client:
                full_prompt = f"{system_prompt}\n\nQ: {prompt}\nA:"
                response = self._generate_gemini_new(full_prompt)
            elif self.backend == 'gemini' and self._gemini_model:
                full_prompt = f"{system_prompt}\n\nQ: {prompt}\nA:"
                response = self._generate_gemini(full_prompt)
            elif self.backend == 'ollama':
                # V5.5: Bracketed labels are safer from accidental stops
                full_prompt = f"{system_prompt}\n{history_str}[User]: {prompt}\n[MEMO]: "
                response = self._generate_ollama(full_prompt)
            else:
                response = self._generate_fallback(prompt)
            
            self.conversation.add("user", prompt)
            self.conversation.add("assistant", response)
            return response
            
        finally:
            self._generate_lock.release()
    
    def _generate_gemini_new(self, prompt: str) -> str:
        if not self._gemini_client:
             return self._generate_fallback(prompt)
        try:
             response = self._gemini_client.models.generate_content(
                 model=self.active_model, contents=prompt
             )
             return response.text.strip()
        except Exception as e:
             print(f"[AI] Gemini New Error: {e}")
             return self._generate_fallback(prompt)

    
    def _generate_prompt(self, prompt_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Create a context-aware system prompt."""
        time_context = self._get_time_context()
        context_str = self._format_context(context)
        
        system_instruction = (
            f"You are MEMO, a witty, helpful, and concise AI companion. "
            f"Current time: {time_context}. "
            f"User context: {context_str}. "
            f"RULES: 1. Be concise (1-2 sentences). 2. Be helpful. 3. STOP generating after your answer."
        )

        prompt = (
            f"{system_instruction}\n\n"
            f"User: {prompt_text}\n"
            f"MEMO:"
        )
        return prompt
    
    def _generate_gemini(self, prompt: str) -> str:
        if not self._gemini_model:
            return self._generate_fallback(prompt)
        
        try:
            response = self._gemini_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 50,
                    'stop_sequences': ["User:", "System:", "\n\n"]
                }
            )
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                print("[AI Gemini] ! Quota exceeded.")
            elif "403" in error_str:
                print("[AI Gemini] ! API Key error.")
            elif "404" in error_str:
                print("[AI Gemini] ! Model not found.")
            return self._generate_fallback(prompt)
    
    def _generate_ollama(self, prompt: str) -> str:
        try:
            import requests
            from interface.dashboard import add_log
            
            # Use /api/generate for completion style (Better for Answer Triggers)
            base_url = self.ollama_url.replace("/api/generate", "").replace("/api/chat", "").rstrip("/")
            
            # V5.0: Prompt is already built in generate()
            prompt_template = prompt
            
            payload = {
                "model": self.ollama_model,
                "prompt": prompt_template,
                "stream": False,
                "options": {
                     "temperature": 0.25,     # keeps witty but not crazy
                     "num_predict": 80,       # HARD length limit
                     "top_p": 0.8,
                     "repeat_penalty": 1.1,
                     "stop": [
                        "[User]:",
                        "[MEMO]:",
                        "example",
                        "Example",
                        "Sure",
                        "sure"
                     ]
                }
            }
            
            add_log(f"Brain is thinking about: {prompt[:30]}...", "ai")
            response = requests.post(f"{base_url}/api/generate", json=payload, timeout=90)

            if response.status_code == 200:
                data = response.json()
                text = data.get('response', '').strip()
                # Simplified cleaning (V5.6)
                for label in ["[MEMO]:", "MEMO:", "[User]:", "[MEMO]"]:
                    if text.startswith(label):
                        text = text[len(label):].strip()
                
                return self._sanitize_response(text, prompt)
            else:
                return f"Brain freeze! (Error {response.status_code})"
                
        except Exception as e:
            print(f"[AI Error] {e}")
            from interface.dashboard import add_log
            add_log(f"AI Error: {e}", "error")
            return self._generate_fallback(prompt)

    def _sanitize_response(self, text: str, user_prompt: str) -> str:
        """Maximum Compatibility Sanitizer (V5.4)."""
        if not text: return ""

        # Remove "AI Assistant" meta-talk
        text = text.replace("As an AI assistant", "As your companion").strip()
        
        # Emoji and Non-ASCII cleanup for smooth TTS
        text = "".join(c for c in text if c.isascii() or c.isalnum() or c in " .,!?-")
        
        # Final cleanup
        text = text.lstrip(" :.,!?-")
        if text and not text.endswith(('.', '!', '?')):
            text += "."
            
        return text[:500].strip()


    def _generate_fallback(self, prompt: str) -> str:
        """Friendly local responses when AI is offline."""
        prompt_lower = prompt.lower()
        
        # Identity queries
        if 'who are you' in prompt_lower or 'your name' in prompt_lower:
            return "I'm MEMO, your desktop buddy! 🤙"
        
        if 'who am i' in prompt_lower or 'my name' in prompt_lower:
            return f"You're {self.user_name}! My favorite human. 😄"

        # General curiosity
        responses = [
            "Ooh, good question! My brain's a bit foggy right now though. ☁️",
            "I'm not exactly sure, but I'm vibes-only right now! 😎",
            "Total mystery to me! Let's just vibe instead. 🤙",
            "I'd look that up for you, but I'm currently in 'chill mode'. 😌",
            "Interesting... I'll have to think about that one! 🤔",
            "You always have the most interesting questions! I'm stumped though. 😄"
        ]
        return random.choice(responses)
    
    # === PLAYFUL PRE-BUILT RESPONSES ===
    
    def startup_message(self) -> str:
        time_period = self._get_time_context()
        
        greetings = {
            'morning': ["Mornin'! ☀️ Let's vibe."],
            'afternoon': ["Yo! Chill afternoon vibes. 🌤️"],
            'evening': ["Evening! What's good? 🌆"],
            'night': ["Night owl crew represent! 🦉"],
        }
        return random.choice(greetings.get(time_period, greetings['afternoon']))
    
    def greeting(self, name: str) -> str:
        self.user_name = name
        return f"Yo {name}! 👊"
    
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
