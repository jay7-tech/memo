# 🤖 MEMO Desktop Companion Robot - Complete Feature Roadmap

> **MEMO** (Memory & Environmental Monitoring Observer) - A vision-first AI desktop companion designed for Raspberry Pi 4B with Logitech Camera

**Last Updated:** January 26, 2026  
**Target Hardware:** Raspberry Pi 4B (4GB/8GB), Logitech USB Camera  
**Author:** Jayadeep / Jay7-Tech

---

## 📋 Table of Contents

1. [Current Features](#-current-features-implemented)
2. [Camera & Vision Features](#-camera--vision-features)
3. [Robot Behavior & Interaction](#-robot-behavior--interaction)
4. [AI & LLM Integration](#-ai--llm-integration)
5. [Hardware Integration](#-hardware-integration-pi4b-specific)
6. [Dashboard & Remote Control](#-dashboard--remote-control)
7. [Security & Privacy Features](#-security--privacy-features)
8. [Implementation Roadmap](#-implementation-roadmap)
9. [Performance Optimization](#-raspberry-pi-4b-performance-tips)
10. [Quick Wins](#-quick-wins)

---

## ✅ Current Features (Implemented)

| Feature | Technology | Module | Status |
|---------|------------|--------|--------|
| **Object Detection** | YOLOv8n | `perception/object_detection.py` | ✅ Working |
| **Pose Estimation** | YOLOv8n-pose (17 keypoints) | `perception/pose_estimation.py` | ✅ Working |
| **Face Recognition** | FaceNet (InceptionResnetV1) | `perception/face_rec.py` | ✅ Working |
| **Spatial Memory** | JSON-based object tracking | `state/scene_state.py` | ✅ Working |
| **Voice Commands** | Speech Recognition | `interface/voice_input.py` | ✅ Working |
| **Text-to-Speech** | PowerShell Speech API | `main.py` | ✅ Working |
| **Focus Mode** | Rule-based distraction detection | `reasoning/rules.py` | ✅ Working |
| **Selfie Capture** | OpenCV | `main.py` | ✅ Working |
| **Web Dashboard** | Flask | `interface/dashboard.py` | ✅ Working |
| **Camera Streaming** | OpenCV + Threading | `camera_input/camera_source.py` | ✅ Working |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MEMO SYSTEM                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Camera    │───▶│  Perception │───▶│    State    │         │
│  │   Input     │    │  (YOLO/Face)│    │  (Memory)   │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│                                                │                 │
│                                                ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Interface  │◀───│  Reasoning  │◀───│   Rules     │         │
│  │ (Voice/Web) │    │  (Events)   │    │  (Logic)    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📸 Camera & Vision Features

### 🔍 Multi-Face Recognition
**Description:** Track and recognize multiple people simultaneously in the frame.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Pi4B Optimized** | Use MobileFaceNet instead of InceptionResnet |
| **Dependencies** | `facenet-pytorch`, custom face tracker |
| **Module** | `perception/face_rec.py` |

**Implementation Notes:**
- Store embeddings for multiple users in a database
- Use Hungarian algorithm for face-to-track assignment
- Consider using `face_recognition` library for Pi4B optimization

---

### 👁️ Eye Gaze Tracking
**Description:** Detect where the user is looking (at screen, away, distracted).

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Pi4B Optimized** | MediaPipe Face Mesh (468 landmarks) |
| **Dependencies** | `mediapipe` |
| **Use Cases** | Attention detection, screen time tracking |

**Implementation Notes:**
```python
# Gaze direction from eye landmarks
# 6 points per eye in Face Mesh
# Calculate pupil position relative to eye corners
```

---

### 😊 Emotion Detection
**Description:** Recognize facial emotions: happy, sad, angry, surprised, neutral, focused, bored.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Pi4B Optimized** | TFLite emotion classifier (~2MB) |
| **Dependencies** | `tflite-runtime`, pre-trained model |
| **Accuracy** | ~85% on FER2013 |

**Recommended Models:**
- `fer2013_mini_XCEPTION` (TFLite) - 2MB
- MobileNet-based emotion classifier
- DeepFace library (if resources allow)

---

### 🎯 Attention Tracking
**Description:** Determine if user is paying attention to the robot/screen.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Dependencies** | Face detection + gaze estimation |
| **Logic** | Face frontal + Eyes looking forward = Attentive |

**States:**
- `ATTENTIVE` - Looking at camera/screen
- `DISTRACTED` - Looking away
- `ABSENT` - No face detected
- `SLEEPING` - Eyes closed for extended period

---

### 🖐️ Hand Gesture Recognition
**Description:** Recognize common hand gestures for quick commands.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Pi4B Optimized** | MediaPipe Hands |
| **Dependencies** | `mediapipe` |
| **Latency** | ~30ms per frame |

**Supported Gestures:**
| Gesture | Action |
|---------|--------|
| 👍 Thumbs Up | Confirm / Like |
| ✋ Open Palm | Stop / Pause |
| ✌️ Peace Sign | Take Selfie |
| 👋 Wave | Hello / Goodbye |
| ☝️ Point Up | Scroll Up |
| 👇 Point Down | Scroll Down |
| 🤙 Call Me | Answer Call |
| ✊ Fist | Start Focus Mode |

---

### 👋 Activity Recognition
**Description:** Detect what the user is doing: typing, reading, drinking, eating, sleeping.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Hard |
| **Approach** | Custom classifier on pose keypoints |
| **Training Data** | Requires labeled activity dataset |

**Detectable Activities:**
- Working at desk (typing posture)
- Reading (head tilt, stable position)
- Drinking (hand to mouth motion)
- Eating (repeated hand-to-mouth)
- Sleeping (head down, eyes closed)
- Stretching (arms raised)
- Phone usage (looking down at hands)

---

### 🔄 Motion Detection
**Description:** Trigger camera/wake on movement in the room.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Method** | Frame differencing + thresholding |
| **Use Cases** | Wake from sleep, security alerts |

**Algorithm:**
```python
# Simple motion detection
prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
diff = cv2.absdiff(prev_gray, curr_gray)
motion_score = np.sum(diff > threshold)
```

---

### 📐 Depth Estimation
**Description:** Monocular depth estimation for spatial awareness.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Pi4B Optimized** | MiDaS-small (TFLite) or stereo camera |
| **Use Cases** | Distance to user, 3D scene understanding |

---

## 🤖 Robot Behavior & Interaction

### 🔊 Wake Word Detection
**Description:** "Hey MEMO" offline activation without cloud dependency.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Library** | OpenWakeWord / Pocketsphinx / Picovoice |
| **Wake Word** | "Hey MEMO", "Hello MEMO", "MEMO" |
| **Latency** | <100ms |

**Recommended Libraries:**
```bash
# OpenWakeWord (best accuracy, MIT license)
pip install openwakeword

# Porcupine (Picovoice - free tier available)
pip install pvporcupine

# Vosk (offline ASR with keyword spotting)
pip install vosk
```

---

### 🎤 Streaming ASR (Automatic Speech Recognition)
**Description:** Real-time speech-to-text transcription.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Options** | Whisper.cpp, Vosk, Google STT |
| **Pi4B Performance** | Vosk recommended (fastest) |

**Comparison:**
| Engine | Speed | Accuracy | Offline | Pi4B |
|--------|-------|----------|---------|------|
| Vosk | Fast | Good | ✅ | ✅ |
| Whisper.cpp | Medium | Excellent | ✅ | ⚠️ Slow |
| Google STT | Fast | Excellent | ❌ | ✅ |

---

### 👀 Head Tracking Gimbal
**Description:** Pan-tilt servo mechanism that follows the user's face.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Hardware** | PCA9685 + 2x SG90/MG90S servos |
| **Control** | PID controller for smooth motion |

**Hardware Setup:**
```
Pi4B GPIO ──► PCA9685 (I2C) ──► Servo Pan (Channel 0)
                            └──► Servo Tilt (Channel 1)
```

**PID Tracking Algorithm:**
```python
# Smooth face tracking
error_x = face_center_x - frame_center_x
error_y = face_center_y - frame_center_y
pan_angle += Kp * error_x + Ki * integral_x + Kd * derivative_x
tilt_angle += Kp * error_y + Ki * integral_y + Kd * derivative_y
```

---

### 😵 Idle Behaviors
**Description:** Random movements and "personality" when not actively engaged.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Implementation** | State machine with timer triggers |

**Idle Behavior Examples:**
- Look around slowly (random pan/tilt)
- "Bored" animation (head tilt, sigh sound)
- "Curious" peek when motion detected
- "Sleepy" head droop after long inactivity
- Random blinks (if LED eyes)

---

### 🗣️ Personalized Responses
**Description:** Different responses based on recognized user identity.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Storage** | `user_profiles.json` |

**Example:**
```json
{
  "Jayadeep": {
    "greeting": "Hello Jay! Ready to be productive?",
    "reminders": ["Take breaks", "Drink water"],
    "preferences": {"voice_speed": 1.2}
  },
  "Guest": {
    "greeting": "Hello! I don't think we've met.",
    "prompt_register": true
  }
}
```

---

### 💡 Emotion-Reactive LEDs
**Description:** Change LED color/pattern based on detected emotion or state.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Hardware** | NeoPixel/WS2812B strip or ring |

**Color Mapping:**
| State/Emotion | LED Color | Pattern |
|---------------|-----------|---------|
| Happy | 🟡 Yellow | Pulse |
| Sad | 🔵 Blue | Slow fade |
| Angry | 🔴 Red | Fast blink |
| Listening | 🟢 Green | Chase |
| Thinking | 🟣 Purple | Breathing |
| Idle | ⚪ White (dim) | Static |
| Focus Mode | 🟠 Orange | Ring |

---

### 📅 Context Awareness
**Description:** Time-based and context-aware responses.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Implementation** | Time-based greeting selection |

**Time-Based Greetings:**
| Time | Greeting |
|------|----------|
| 5:00 - 12:00 | "Good morning, [Name]!" |
| 12:00 - 17:00 | "Good afternoon, [Name]!" |
| 17:00 - 21:00 | "Good evening, [Name]!" |
| 21:00 - 5:00 | "Working late, [Name]?" |

---

### 🧠 Conversation Memory
**Description:** Remember past conversations and context for each user.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Storage** | SQLite or JSON |
| **Context Window** | Last 10 turns per user |

**Schema:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    timestamp DATETIME,
    user_message TEXT,
    bot_response TEXT,
    context_tags TEXT
);
```

---

### 🎭 Personality Modes
**Description:** Switch between different interaction styles.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **Implementation** | LLM system prompt switching |

**Available Personalities:**
| Mode | Description | Trigger |
|------|-------------|---------|
| **Helpful** | Professional assistant | Default |
| **Sarcastic** | Witty, playful responses | "Be sarcastic" |
| **Cute** | Kawaii, encouraging | "Be cute" |
| **Strict** | Focus coach, firm | During Focus Mode |
| **Pirate** | Arrr matey! | Easter egg |

---

## 🧠 AI & LLM Integration

### 💬 Gemini/GPT Chat
**Description:** Natural conversational AI with context awareness.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Easy |
| **API** | Google Gemini 1.5 Flash (free tier) |
| **Latency** | ~500ms |

**Implementation:**
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

def chat(user_message, context):
    prompt = f"""You are MEMO, a helpful desktop companion.
    User: {user_message}
    Context: {context}
    Respond concisely and helpfully."""
    response = model.generate_content(prompt)
    return response.text
```

---

### 🖼️ Vision-Language Model
**Description:** Describe what the robot sees, answer visual questions.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **API** | Gemini Vision / GPT-4V |
| **Use Cases** | "What do you see?", "Is my room messy?" |

**Example Queries:**
- "What's on my desk right now?"
- "Can you see my coffee mug?"
- "Describe my room"
- "Is someone behind me?"

---

### 📚 RAG System (Retrieval-Augmented Generation)
**Description:** Answer questions about personal documents.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Hard |
| **Components** | ChromaDB + Sentence Transformers |
| **Use Cases** | "What was in my notes about X?" |

---

### 🔊 Voice Cloning
**Description:** Speak in a custom or cloned voice.

| Attribute | Value |
|-----------|-------|
| **Difficulty** | Medium |
| **Options** | Edge-TTS, ElevenLabs API, Coqui TTS |

**Recommended:**
```bash
# Edge-TTS (Free, many voices)
pip install edge-tts
edge-tts --voice en-US-GuyNeural --text "Hello!" --write-media out.mp3
```

---

## 🎛️ Hardware Integration (Pi4B Specific)

### Recommended Components

| Component | Part | Price | Purpose |
|-----------|------|-------|---------|
| **Servo Controller** | PCA9685 | $5 | Control pan/tilt servos |
| **Pan Servo** | SG90 / MG90S | $3 | Horizontal head movement |
| **Tilt Servo** | SG90 / MG90S | $3 | Vertical head movement |
| **Microphone** | ReSpeaker 4-Mic Array | $30 | Superior voice capture |
| **Speaker** | USB Speaker / I2S DAC | $10 | Audio output |
| **LED Eyes** | WS2812B Ring (16 LED) | $5 | Expressive eyes |
| **OLED Display** | SSD1306 128x64 | $5 | Robot face display |
| **Environment Sensor** | DHT22 | $4 | Temperature & humidity |
| **Air Quality** | MQ-135 | $3 | CO2 / VOC detection |
| **Touch Sensor** | MPR121 | $5 | Capacitive touch input |
| **IR Blaster** | IR LED + TSOP38238 | $2 | Control TV/AC |
| **UPS HAT** | Various | $25 | Graceful shutdown |

### GPIO Pinout Reference

```
┌─────────────────────────────────────────┐
│           Raspberry Pi 4B GPIO          │
├─────────────────────────────────────────┤
│  3.3V  [1]  [2]  5V                     │
│  SDA   [3]  [4]  5V      ──► PCA9685    │
│  SCL   [5]  [6]  GND                    │
│  GPIO4 [7]  [8]  TXD                    │
│  GND   [9]  [10] RXD                    │
│  GPIO17[11] [12] GPIO18  ──► NeoPixel   │
│  GPIO27[13] [14] GND                    │
│  GPIO22[15] [16] GPIO23                 │
│  3.3V  [17] [18] GPIO24  ──► DHT22      │
│  MOSI  [19] [20] GND                    │
│  MISO  [21] [22] GPIO25                 │
│  SCLK  [23] [24] CE0                    │
│  GND   [25] [26] CE1                    │
│  ID_SD [27] [28] ID_SC                  │
│  GPIO5 [29] [30] GND                    │
│  GPIO6 [31] [32] GPIO12  ──► IR LED     │
│  GPIO13[33] [34] GND                    │
│  GPIO19[35] [36] GPIO16                 │
│  GPIO26[37] [38] GPIO20                 │
│  GND   [39] [40] GPIO21                 │
└─────────────────────────────────────────┘
```

---

## 🌐 Dashboard & Remote Control

### Features to Implement

| Feature | Description | Priority |
|---------|-------------|----------|
| **📊 Live Stats** | CPU, RAM, temp, FPS | High |
| **🗺️ Object Map** | 2D visualization of detected objects | Medium |
| **📱 Mobile PWA** | Progressive Web App for mobile | Medium |
| **🔔 Push Notifications** | Alerts via web push | Low |
| **📹 Video Recording** | Record clips on motion | Medium |
| **🕐 Activity Timeline** | History with thumbnails | Medium |
| **⚙️ Settings Panel** | Configure thresholds | High |

### Dashboard API Endpoints

```
GET  /api/status        - System status (CPU, RAM, etc.)
GET  /api/stream        - MJPEG video stream
GET  /api/objects       - Currently detected objects
GET  /api/state         - Full scene state
POST /api/command       - Send command (focus on/off, etc.)
GET  /api/history       - Activity log
POST /api/settings      - Update configuration
```

---

## 🔐 Security & Privacy Features

| Feature | Description | Implementation |
|---------|-------------|----------------|
| **🚨 Intruder Detection** | Alert if unknown face | Compare embedding, if no match → alert |
| **🔒 Privacy Mode** | Quick camera/mic shutoff | Hardware switch or command |
| **📦 Package Detection** | Detect deliveries | Train YOLO on package images |
| **🚪 Door Monitoring** | Detect door open/close | Motion detection in door region |
| **🎭 Face Blur** | Blur non-registered faces | Apply Gaussian blur to unknown faces |
| **🔐 Local Processing** | All data stays on device | No cloud upload of images |

---

## 🏗️ Implementation Roadmap

### Phase 1: Core Pi4B Migration (Week 1-2)

| Task | Status | Notes |
|------|--------|-------|
| Optimize camera for Pi4B (480p) | 🔲 | Reduce resolution for speed |
| Convert models to TFLite/ONNX | 🔲 | 2-3x speedup |
| Add offline wake word | 🔲 | OpenWakeWord recommended |
| Set up head tracking gimbal | 🔲 | PCA9685 + 2x servos |

### Phase 2: Enhanced Perception (Week 3-4)

| Task | Status | Notes |
|------|--------|-------|
| Hand gesture recognition | 🔲 | MediaPipe Hands |
| Eye gaze / attention tracking | 🔲 | MediaPipe Face Mesh |
| Emotion detection | 🔲 | TFLite model |
| Motion-triggered wake | 🔲 | Frame differencing |

### Phase 3: Smart Interaction (Week 5-6)

| Task | Status | Notes |
|------|--------|-------|
| Gemini integration | 🔲 | Natural conversation |
| Vision-Language model | 🔲 | "What do you see?" |
| Personalized responses | 🔲 | Per-user profiles |
| Conversation memory | 🔲 | SQLite storage |

### Phase 4: Hardware Polish (Week 7-8)

| Task | Status | Notes |
|------|--------|-------|
| LED eyes/expressions | 🔲 | NeoPixel ring |
| Environment sensors | 🔲 | DHT22, MQ-135 |
| Better audio setup | 🔲 | ReSpeaker array |
| Idle behaviors | 🔲 | State machine |

---

## ⚡ Raspberry Pi 4B Performance Tips

### Model Optimization

| Optimization | Speedup | How |
|--------------|---------|-----|
| **YOLOv8n INT8** | 2-3x | `yolo export format=tflite int8=True` |
| **MediaPipe** | Native | Already optimized for ARM |
| **ONNX Runtime** | 1.5x | `pip install onnxruntime` |
| **TFLite** | 2x | Quantized models |

### Processing Optimization

| Technique | Benefit |
|-----------|---------|
| Process every 3rd frame | 3x effective FPS |
| Lower resolution (480x360) | 2x speedup |
| Async inference threading | Better responsiveness |
| Batch processing | GPU utilization |

### System Optimization

```bash
# Increase GPU memory
sudo raspi-config
# → Performance Options → GPU Memory → 256

# Enable hardware acceleration
export LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Overclock (with cooling)
# Edit /boot/config.txt
# over_voltage=6
# arm_freq=2000
```

---

## 🎯 Quick Wins

Features you can implement in under a day:

### 1. Motion Detection (2 hours)
```python
# Add to main.py
def detect_motion(prev_frame, curr_frame, threshold=25):
    diff = cv2.absdiff(
        cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    )
    motion_pixels = np.sum(diff > threshold)
    return motion_pixels > 5000  # Adjust threshold
```

### 2. Time-Based Greetings (30 minutes)
```python
from datetime import datetime

def get_greeting(name):
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return f"Good morning, {name}!"
    elif 12 <= hour < 17:
        return f"Good afternoon, {name}!"
    elif 17 <= hour < 21:
        return f"Good evening, {name}!"
    else:
        return f"Working late, {name}?"
```

### 3. Wake Word with OpenWakeWord (1 hour)
```bash
pip install openwakeword
```

### 4. NeoPixel LED Feedback (2 hours)
```python
from rpi_ws281x import PixelStrip, Color

LED_PIN = 18
LED_COUNT = 16

strip = PixelStrip(LED_COUNT, LED_PIN)
strip.begin()

def set_mood(emotion):
    colors = {
        "happy": Color(255, 255, 0),
        "sad": Color(0, 0, 255),
        "angry": Color(255, 0, 0),
        "neutral": Color(100, 100, 100)
    }
    for i in range(LED_COUNT):
        strip.setPixelColor(i, colors.get(emotion, Color(255,255,255)))
    strip.show()
```

### 5. Simple Gesture Detection (3 hours)
```python
import mediapipe as mp

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)

def detect_gesture(frame):
    results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if results.multi_hand_landmarks:
        # Thumbs up detection logic
        landmarks = results.multi_hand_landmarks[0].landmark
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        if thumb_tip.y < thumb_ip.y:  # Thumb pointing up
            return "thumbs_up"
    return None
```

---

## 📚 Resources & References

### Libraries & Frameworks
- [YOLOv8 (Ultralytics)](https://github.com/ultralytics/ultralytics)
- [MediaPipe](https://mediapipe.dev/)
- [OpenWakeWord](https://github.com/dscripka/openWakeWord)
- [Vosk ASR](https://alphacephei.com/vosk/)
- [Google Gemini API](https://ai.google.dev/)
- [Edge-TTS](https://github.com/rany2/edge-tts)

### Hardware Guides
- [PCA9685 Servo Driver](https://learn.adafruit.com/16-channel-pwm-servo-driver)
- [ReSpeaker Setup](https://wiki.seeedstudio.com/ReSpeaker_4_Mic_Array_for_Raspberry_Pi/)
- [NeoPixel with Pi](https://learn.adafruit.com/neopixels-on-raspberry-pi)

### Model Downloads
- [YOLOv8n TFLite](https://github.com/ultralytics/ultralytics)
- [Emotion Detection TFLite](https://github.com/oarriaga/face_classification)
- [MiDaS Depth](https://github.com/isl-org/MiDaS)

---

## 🤝 Contributing

Want to add a feature? 

1. Check the roadmap above
2. Create a new module in the appropriate folder
3. Follow the existing code style
4. Test on Raspberry Pi 4B
5. Submit a PR!

---

## 📄 License

MIT License - Feel free to use and modify!

---

**Made with ❤️ by Jayadeep / Jay7-Tech**
