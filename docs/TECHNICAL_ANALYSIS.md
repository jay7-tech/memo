# 🔍 MEMO - Technical Analysis & Improvement Roadmap

## Executive Summary

This document identifies **inefficiencies, impractical features, and real-world limitations** in MEMO that would affect its use as a practical companion bot. Each issue includes severity, impact, and recommended fixes.

---

## 🚨 CRITICAL ISSUES (Must Fix)

### 1. Voice Input Requires Internet Connection
**File:** `interface/voice_input.py` (line 39)

**Problem:**
```python
text = recognizer.recognize_google(audio).lower()  # Uses Google Cloud!
```
- Uses Google Speech API which **requires internet**
- Privacy concern - audio sent to Google servers
- **Fails completely offline** - unusable for a standalone robot

**Impact:** ⭐⭐⭐⭐⭐ Companion bot unusable without WiFi

**Fix:**
```python
# Use Vosk (already installed) for offline recognition
from vosk import Model, KaldiRecognizer
model = Model("models/vosk/vosk-model-en")
recognizer = KaldiRecognizer(model, 16000)
# Process audio locally - no internet needed
```

---

### 2. Face Recognition Only Supports ONE User
**File:** `perception/face_rec.py` (lines 129-147)

**Problem:**
```python
# Only stores single user embedding
np.save("user_embedding.npy", embedding)  # Overwrites previous user!
```
- Can only remember **1 person**
- Registering new user **deletes** previous user
- No multi-user household support

**Impact:** ⭐⭐⭐⭐⭐ Family/office use impossible

**Fix:**
```python
# Use dictionary of users
self.users = {}  # {"name": embedding}
# Save to users.json with all embeddings
# Match against all users, return best match
```

---

### 3. TTS Creates New Engine Every Request (Performance Killer)
**File:** `interface/tts_engine.py` (lines 65-80)

**Problem:**
```python
def _create_pyttsx3_engine(self):
    engine = pyttsx3.init()  # Called EVERY time we speak!
```
- Creates new pyttsx3 instance **for each sentence**
- ~200ms overhead per speech request
- Resource leak on Raspberry Pi

**Impact:** ⭐⭐⭐⭐ Laggy responses, memory issues

**Fix:**
```python
# Create engine ONCE at startup
def __init__(self):
    self._engine = pyttsx3.init()
    self._engine_lock = threading.Lock()

def speak(self, text):
    with self._engine_lock:
        self._engine.say(text)
        self._engine.runAndWait()
```

---

## ⚠️ MAJOR ISSUES (Should Fix)

### 4. Query Handler Has Very Limited Understanding
**File:** `interface/query_handler.py`

**Problem:**
- Only understands 2 query patterns: "where is X" and "is X here"
- No natural language understanding
- Can't handle variations like "find my phone", "locate the remote"

**Current Patterns:**
```python
r"where is (.+)\??"
r"(is|do (you|u) see|can (you|u) see) (.+)"
```

**Impact:** ⭐⭐⭐⭐ Users feel bot is "dumb"

**Fix:**
```python
# Add more patterns or use intent classification
INTENT_PATTERNS = {
    'locate': [r'where is', r'find', r'locate', r'look for', r'search for'],
    'check': [r'is there', r'do you see', r'can you see', r'is .+ here'],
    'count': [r'how many', r'count'],
    'describe': [r'what do you see', r'describe', r'what.s here']
}
# Or integrate with LLM for natural queries
```

---

### 5. Gesture Recognition Requires MediaPipe (Fails on Pi)
**File:** `perception/gesture_recognizer.py`

**Problem:**
```python
HAS_MEDIAPIPE = False
# Falls back to OpenCV skin detection - VERY unreliable
```
- MediaPipe doesn't work on Raspberry Pi ARM
- OpenCV fallback uses skin color detection (fails with different skin tones)
- No gesture actions are actually implemented!

**Impact:** ⭐⭐⭐⭐ Feature completely broken on Pi

**Fix:**
```python
# Option 1: Use YOLO hand detection (works on ARM)
# Option 2: Train a lightweight CNN for gesture classification
# Option 3: Remove feature entirely if not working
```

---

### 6. Pose Detection Only Detects Sitting/Standing
**File:** `state/scene_state.py` (lines 176-229)

**Problem:**
```python
def _determine_pose(self, keypoints):
    # Only returns: "sitting", "standing", or "unknown"
```
- Very basic - only 2 poses
- No detection of: sleeping, exercising, typing, on phone, eating
- Can't detect activities that matter for a companion

**Impact:** ⭐⭐⭐ Limited contextual awareness

**Fix:**
```python
POSES = {
    'sitting': detect_sitting,
    'standing': detect_standing,
    'lying_down': detect_lying,
    'exercising': detect_exercise,
    'typing': detect_typing,  # Wrist position + no phone
    'on_phone': detect_phone_use,  # Phone near ear
    'eating': detect_eating,  # Hand to mouth motion
}
```

---

### 7. Rules Engine Has Hardcoded Timings
**File:** `reasoning/rules.py`

**Problem:**
```python
demo_threshold = 60  # seconds - hardcoded!
if timestamp - self.last_focus_alert > 5.0:  # hardcoded!
if timestamp - self.last_proximity_alert > 15.0:  # hardcoded!
```
- All timings are hardcoded, not configurable
- No user preferences for alert frequency
- Can't adjust for different use cases

**Impact:** ⭐⭐⭐ Annoying alerts, no customization

**Fix:**
```python
# Load from config
self.config = {
    'sitting_reminder_seconds': 2700,  # 45 mins (not 60s demo)
    'focus_alert_cooldown': 10.0,
    'proximity_cooldown': 30.0,
    'greeting_reset_time': 300.0
}
```

---

### 8. Hydration Helper Does Nothing
**File:** `reasoning/rules.py` (lines 165-171)

**Problem:**
```python
if 'bottle' in scene_state.objects:
    pass  # Literally does nothing!
```
- Feature mentioned in docs but **not implemented**
- No reminder to drink water
- No tracking of bottle usage

**Impact:** ⭐⭐⭐ Dead code, missing feature

**Fix:**
```python
# Track bottle interactions
if 'bottle' in scene_state.objects:
    self.last_bottle_seen = timestamp
elif timestamp - self.last_bottle_seen > 3600:  # 1 hour
    events.append("TTS: Don't forget to drink water!")
```

---

## 🔧 MODERATE ISSUES (Nice to Fix)

### 9. No Error Recovery for Camera
**File:** `main.py`

**Problem:**
- If camera disconnects, system crashes
- No reconnection logic
- No fallback to secondary camera

**Fix:**
```python
def get_frame_safe(self):
    try:
        return self.cam.read()
    except:
        self._reconnect()
        return None
```

---

### 10. Dashboard Sends Full Frame Every Update
**File:** `interface/dashboard.py`

**Problem:**
- Sends entire JPEG frame via WebSocket
- Bandwidth heavy on network
- Should use progressive JPEG or video stream

**Fix:**
```python
# Use MJPEG streaming or WebRTC for efficiency
# Or send only changed regions
```

---

### 11. Object Memory Never Expires
**File:** `state/scene_state.py`

**Problem:**
```python
self.objects[label] = {...}  # Kept forever!
```
- Objects from hours ago still in memory
- "Where is X" returns stale data
- Memory grows indefinitely

**Fix:**
```python
def cleanup_old_objects(self, max_age=300):
    """Remove objects not seen in 5 minutes."""
    now = time.time()
    self.objects = {k: v for k, v in self.objects.items() 
                    if now - v['last_seen'] < max_age}
```

---

### 12. Face Recognition Uses Rough Pose-Based Face Box
**File:** `main.py` (lines 258-279)

**Problem:**
```python
# Uses nose + ear keypoints to estimate face box
ear_dist = abs(l_ear[0] - r_ear[0])
face_w = int(ear_dist * 2.0)  # Rough estimate!
```
- No proper face detector
- Face box estimation is inaccurate
- Recognition fails when pose keypoints are wrong

**Fix:**
```python
# Use dedicated face detector
from facenet_pytorch import MTCNN
mtcnn = MTCNN(keep_all=False)
boxes, probs = mtcnn.detect(frame)
```

---

### 13. No Conversation Context
**File:** `interface/query_handler.py`

**Problem:**
- Each query is independent
- Can't reference previous interactions
- "What about the cup?" fails (no context)

**Fix:**
```python
class QueryHandler:
    def __init__(self):
        self.last_object_mentioned = None
        self.conversation_history = []
    
    def handle_query(self, query, scene_state):
        if "it" in query or "that" in query:
            # Replace with last mentioned object
            query = query.replace("it", self.last_object_mentioned)
```

---

## 📊 INEFFICIENCY SUMMARY

| Component | Issue | Severity | Effort to Fix |
|-----------|-------|----------|---------------|
| Voice Input | Requires internet | 🔴 Critical | Medium |
| Face Recognition | Single user only | 🔴 Critical | Medium |
| TTS Engine | Recreates engine | 🔴 Critical | Low |
| Query Handler | Limited patterns | 🟠 Major | Medium |
| Gesture Recognition | Broken on Pi | 🟠 Major | High |
| Pose Detection | Only 2 poses | 🟠 Major | Medium |
| Rules Engine | Hardcoded timings | 🟠 Major | Low |
| Hydration Helper | Not implemented | 🟠 Major | Low |
| Camera | No reconnection | 🟡 Moderate | Low |
| Dashboard | Bandwidth heavy | 🟡 Moderate | Medium |
| Object Memory | Never expires | 🟡 Moderate | Low |
| Face Box | Inaccurate | 🟡 Moderate | Medium |
| Conversation | No context | 🟡 Moderate | Medium |

---

## 🎯 RECOMMENDED PRIORITY ORDER

### Phase 1: Core Fixes (Week 1)
1. ✅ Fix TTS engine (reuse engine instance)
2. ⬜ Add offline voice (Vosk integration)
3. ⬜ Multi-user face recognition
4. ⬜ Make rule timings configurable

### Phase 2: Usability (Week 2)
5. ⬜ Expand query patterns
6. ⬜ Implement hydration reminders
7. ⬜ Add object memory cleanup
8. ⬜ Camera reconnection logic

### Phase 3: Intelligence (Week 3+)
9. ⬜ Activity recognition (not just sitting/standing)
10. ⬜ Conversation context
11. ⬜ LLM integration for natural queries
12. ⬜ Better face detection (MTCNN)

---

## 🚀 QUICK WINS (Can Fix Today)

### 1. Fix Hydration Helper (5 minutes)
```python
# In rules.py, replace pass with:
if 'bottle' not in current_visible_objects:
    if not hasattr(self, 'last_bottle_seen'):
        self.last_bottle_seen = timestamp
    elif timestamp - self.last_bottle_seen > 1800:  # 30 mins
        events.append("TTS: Remember to drink some water!")
        self.last_bottle_seen = timestamp
```

### 2. Add Object Cleanup (5 minutes)
```python
# In scene_state.py, add to update():
# Cleanup old objects
self.objects = {k: v for k, v in self.objects.items() 
                if timestamp - v['last_seen'] < 300}
```

### 3. Make Rules Configurable (10 minutes)
```python
# In rules.py __init__:
self.config = {
    'sitting_reminder': 2700,  # 45 minutes
    'focus_cooldown': 10,
    'proximity_cooldown': 30,
}
```

---

## 📝 Conclusion

MEMO has a solid foundation but several features are:
- **Not implemented** (hydration helper)
- **Internet-dependent** (voice recognition)
- **Single-user limited** (face recognition)
- **Unreliable on target hardware** (gestures on Pi)

Fixing the **Critical Issues** first will make MEMO a practical, usable companion robot. The architecture is clean enough that most fixes are straightforward.
