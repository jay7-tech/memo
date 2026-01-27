# MEMO API Reference
> Complete API documentation for all MEMO modules

**Last Updated:** January 26, 2026  
**Author:** Jayadeep / Jay7-Tech

---

## 📋 Table of Contents

1. [Perception Module](#-perception-module)
   - [ObjectDetector](#objectdetector)
   - [FaceRecognizer](#facerecognizer)
   - [PoseEstimator](#poseestimator)
2. [State Module](#-state-module)
   - [SceneState](#scenestate)
3. [Reasoning Module](#-reasoning-module)
   - [RulesEngine](#rulesengine)
4. [Interface Module](#-interface-module)
   - [QueryHandler](#queryhandler)
   - [VoiceInput](#voiceinput)
5. [Camera Module](#-camera-module)
   - [CameraSource](#camerasource)

---

## 🔍 Perception Module

### ObjectDetector

**Location:** `perception/object_detection.py`

**Purpose:** Real-time object detection using YOLOv8.

#### Constructor

```python
ObjectDetector(model_name: str = 'yolov8n.pt')
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | str | `'yolov8n.pt'` | YOLOv8 model variant |

**Model Options:**
| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `yolov8n.pt` | 6MB | Fastest | Good |
| `yolov8s.pt` | 22MB | Fast | Better |
| `yolov8m.pt` | 52MB | Medium | High |
| `yolov8l.pt` | 84MB | Slow | Higher |
| `yolov8x.pt` | 131MB | Slowest | Highest |

#### Methods

##### `detect(frame) → list[dict]`

Detect objects in a video frame.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `frame` | `numpy.ndarray` | BGR image (H×W×3) |

**Returns:**
```python
[
    {
        "label": "person",           # Object class name
        "bbox": [100, 50, 200, 300], # [x, y, width, height]
        "confidence": 0.92           # 0.0 to 1.0
    },
    ...
]
```

**Example:**
```python
detector = ObjectDetector()
frame = cv2.imread('desk.jpg')
detections = detector.detect(frame)

for det in detections:
    x, y, w, h = det['bbox']
    label = det['label']
    cv2.rectangle(frame, (int(x), int(y)), (int(x+w), int(y+h)), (0, 255, 0), 2)
    cv2.putText(frame, label, (int(x), int(y)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
```

---

### FaceRecognizer

**Location:** `perception/face_rec.py`

**Purpose:** Face recognition using FaceNet (InceptionResnetV1).

#### Constructor

```python
FaceRecognizer()
```

Automatically loads saved user profile from `user_embedding.npy` and `user_name.txt` if they exist.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `device` | str | `'cpu'` or `'cuda'` |
| `resnet` | Model | InceptionResnetV1 model |
| `known_embedding` | ndarray | 512-dim embedding of registered user |
| `user_name` | str | Name of registered user |

#### Methods

##### `load_user() → None`

Load saved user profile from disk.

**Files:**
- `user_embedding.npy` - 512-dimensional numpy array
- `user_name.txt` - Plain text name

---

##### `save_user(embedding, name) → None`

Save user profile to disk.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `embedding` | `numpy.ndarray` | 512-dim face embedding |
| `name` | `str` | User's name |

---

##### `get_embedding(face_crop) → numpy.ndarray | None`

Extract face embedding from a cropped face image.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `face_crop` | `numpy.ndarray` | BGR face image (any size) |

**Returns:** 512-dimensional embedding vector, or `None` if invalid input.

**Processing Steps:**
1. Resize to 160×160
2. Convert BGR → RGB
3. Normalize: `(x - 127.5) / 128.0`
4. Forward pass through InceptionResnetV1

---

##### `recognize(frame, bbox) → str | None`

Recognize a face in the frame.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `frame` | `numpy.ndarray` | Full BGR frame |
| `bbox` | `list[float]` | Bounding box `[x, y, w, h]` |

**Returns:** 
- User's name if cosine similarity > 0.6
- `None` if no match or no registered user

**Example:**
```python
face_rec = FaceRecognizer()
identity = face_rec.recognize(frame, [100, 50, 150, 150])
if identity:
    print(f"Hello, {identity}!")
```

---

##### `register_face(frame, bbox, name) → bool`

Register a new user's face.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `frame` | `numpy.ndarray` | - | Full BGR frame |
| `bbox` | `list[float]` | - | Face bounding box |
| `name` | `str` | `"User"` | User's name |

**Returns:** `True` if successful, `False` otherwise.

**Example:**
```python
face_rec = FaceRecognizer()
success = face_rec.register_face(frame, [100, 50, 150, 150], "Jayadeep")
if success:
    print("Face registered successfully!")
```

---

### PoseEstimator

**Location:** `perception/pose_estimation.py`

**Purpose:** Human pose estimation using YOLOv8-pose.

#### Constructor

```python
PoseEstimator(model_name: str = 'yolov8n-pose.pt')
```

#### Keypoint Mapping (COCO Format)

| Index | Name | Description |
|-------|------|-------------|
| 0 | NOSE | Nose tip |
| 1 | LEFT_EYE | Left eye center |
| 2 | RIGHT_EYE | Right eye center |
| 3 | LEFT_EAR | Left ear |
| 4 | RIGHT_EAR | Right ear |
| 5 | LEFT_SHOULDER | Left shoulder |
| 6 | RIGHT_SHOULDER | Right shoulder |
| 7 | LEFT_ELBOW | Left elbow |
| 8 | RIGHT_ELBOW | Right elbow |
| 9 | LEFT_WRIST | Left wrist |
| 10 | RIGHT_WRIST | Right wrist |
| 11 | LEFT_HIP | Left hip |
| 12 | RIGHT_HIP | Right hip |
| 13 | LEFT_KNEE | Left knee |
| 14 | RIGHT_KNEE | Right knee |
| 15 | LEFT_ANKLE | Left ankle |
| 16 | RIGHT_ANKLE | Right ankle |

#### Methods

##### `estimate(frame) → dict | None`

Estimate pose from a video frame.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `frame` | `numpy.ndarray` | BGR image |

**Returns:**
```python
{
    "keypoints": {
        "NOSE": (320, 150),
        "LEFT_SHOULDER": (280, 200),
        "RIGHT_SHOULDER": (360, 200),
        # ... 17 keypoints total
    },
    "bbox": [100, 50, 400, 500]  # [x, y, w, h]
}
```

**Returns `None` if no person detected with sufficient keypoints.**

---

## 📦 State Module

### SceneState

**Location:** `state/scene_state.py`

**Purpose:** Global state management for objects and human presence.

#### Constructor

```python
SceneState()
```

Automatically loads previous state from `memory.json` if it exists.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `objects` | `dict` | Tracked objects dictionary |
| `human` | `dict` | Human state dictionary |
| `focus_mode` | `bool` | Focus mode flag |
| `register_trigger` | `bool` | Face registration trigger |
| `register_name` | `str` | Name for face registration |
| `selfie_trigger` | `bool` | Selfie capture trigger |
| `width` | `int` | Frame width |

#### Data Structures

##### Objects Dictionary
```python
{
    'bottle': {
        'last_seen': 1706284200.5,     # Unix timestamp
        'bbox': [100, 200, 50, 80],    # [x, y, w, h]
        'position': 'left'              # 'left', 'center', 'right'
    },
    'laptop': {
        'last_seen': 1706284200.5,
        'bbox': [200, 150, 300, 200],
        'position': 'center'
    }
}
```

##### Human Dictionary
```python
{
    'present': True,
    'pose_state': 'sitting',       # 'sitting', 'standing', 'unknown'
    'keypoints': {
        'NOSE': (320, 150),
        'LEFT_SHOULDER': (280, 200),
        # ...
    },
    'last_seen': 1706284200.5,     # Unix timestamp
    'identity': 'Jayadeep',        # or None if unknown
    'pose_start_time': 1706280600  # When current pose started
}
```

#### Methods

##### `update(detections, pose_data, timestamp, frame_width, frame_height) → None`

Update state with new frame data.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `detections` | `list[dict]` | - | From ObjectDetector |
| `pose_data` | `dict` | - | From PoseEstimator |
| `timestamp` | `float` | - | Current time (Unix) |
| `frame_width` | `int` | 640 | Frame width |
| `frame_height` | `int` | 480 | Frame height |

---

##### `save_memory() → None`

Persist current state to `memory.json`.

**Saved Fields:**
- `objects` dictionary
- `focus_mode` flag

---

##### `load_memory() → None`

Load state from `memory.json`.

---

##### `get_object_state(label) → dict | None`

Get state of a specific object.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `label` | `str` | Object label (e.g., 'bottle') |

**Returns:** Object state dict or `None` if not found.

---

##### `get_last_seen(label) → float | None`

Get last seen timestamp for an object.

---

## 🧠 Reasoning Module

### RulesEngine

**Location:** `reasoning/rules.py`

**Purpose:** Event generation based on state changes.

#### Constructor

```python
RulesEngine()
```

#### Methods

##### `check_rules(scene_state, timestamp) → list[str]`

Analyze scene state and generate events.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `scene_state` | `SceneState` | Current scene state |
| `timestamp` | `float` | Current Unix timestamp |

**Returns:** List of event strings.

**Event Types:**
| Event Pattern | Trigger |
|---------------|---------|
| `"Object appeared: {label}"` | New object visible |
| `"Object disappeared: {label}"` | Object no longer visible |
| `"TTS: You have been sitting..."` | Sitting > 60 seconds |
| `"TTS: Put the phone away..."` | Cell phone in focus mode |
| `"TTS: You are too close..."` | Shoulders > 55% of frame |
| `"TTS: Hello {name}..."` | Known user recognized |

**Example:**
```python
engine = RulesEngine()

while running:
    events = engine.check_rules(scene_state, time.time())
    
    for event in events:
        if event.startswith("TTS:"):
            speak(event[4:])  # Send to TTS engine
        else:
            print(event)       # Log to console
```

---

## 🎤 Interface Module

### QueryHandler

**Location:** `interface/query_handler.py`

**Purpose:** Handle natural language queries about scene state.

#### Methods

##### `handle_query(query, scene_state) → str`

Process a user query and return a response.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `query` | `str` | User's question |
| `scene_state` | `SceneState` | Current scene state |

**Supported Query Patterns:**
| Query Pattern | Response Type |
|--------------|---------------|
| `"where is my {object}?"` | Object location |
| `"what do you see?"` | List of visible objects |
| `"am I sitting or standing?"` | Pose state |
| `"focus on"` | Enable focus mode |
| `"focus off"` | Disable focus mode |
| `"take a selfie"` | Trigger camera capture |
| `"register my face as {name}"` | Register new user |

---

### VoiceInput

**Location:** `interface/voice_input.py`

**Purpose:** Speech-to-text input handling.

#### Constructor

```python
VoiceInput(callback: Callable[[str], None])
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `callback` | `Callable` | Function called with transcribed text |

#### Methods

##### `start() → None`
Start listening for voice input in a background thread.

##### `stop() → None`
Stop voice input thread.

---

## 📸 Camera Module

### CameraSource

**Location:** `camera_input/camera_source.py`

**Purpose:** Camera capture with threading for low latency.

#### Constructor

```python
CameraSource(source=0, width=640, height=480, rotation=0)
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `int | str` | 0 | Camera index or URL |
| `width` | `int` | 640 | Frame width |
| `height` | `int` | 480 | Frame height |
| `rotation` | `int` | 0 | Rotation in degrees (0, 90, 180, 270) |

#### Methods

##### `read() → tuple[bool, numpy.ndarray]`

Get the latest frame.

**Returns:** `(success: bool, frame: ndarray)`

---

##### `release() → None`

Release camera resources.

---

## 🔧 Utility Functions

### Main Loop Structure

```python
from camera_input import CameraSource
from perception import ObjectDetector, PoseEstimator, FaceRecognizer
from state import SceneState
from reasoning import RulesEngine
from interface import QueryHandler

# Initialize components
camera = CameraSource(source=0)
detector = ObjectDetector('yolov8n.pt')
pose_estimator = PoseEstimator('yolov8n-pose.pt')
face_rec = FaceRecognizer()
scene_state = SceneState()
rules_engine = RulesEngine()
query_handler = QueryHandler()

# Main loop
while running:
    ret, frame = camera.read()
    if not ret:
        continue
    
    timestamp = time.time()
    
    # Perception
    detections = detector.detect(frame)
    pose_data = pose_estimator.estimate(frame)
    
    # Face recognition
    for det in detections:
        if det['label'] == 'person':
            identity = face_rec.recognize(frame, det['bbox'])
            if identity:
                scene_state.human['identity'] = identity
    
    # State update
    scene_state.update(detections, pose_data, timestamp)
    
    # Rules processing
    events = rules_engine.check_rules(scene_state, timestamp)
    
    # Handle events
    for event in events:
        process_event(event)

camera.release()
```

---

## 📊 Performance Benchmarks

### Raspberry Pi 4B (4GB RAM)

| Module | Resolution | FPS | Notes |
|--------|------------|-----|-------|
| ObjectDetector (yolov8n) | 480×360 | ~8 | Every 3rd frame |
| PoseEstimator | 480×360 | ~6 | Every 3rd frame |
| FaceRecognizer | 160×160 | ~20 | On demand |
| Combined Pipeline | 480×360 | ~5 | All modules |

### Desktop (CUDA)

| Module | Resolution | FPS | Notes |
|--------|------------|-----|-------|
| ObjectDetector (yolov8n) | 640×480 | ~60 | Real-time |
| PoseEstimator | 640×480 | ~45 | Real-time |
| FaceRecognizer | 160×160 | ~100 | On demand |
| Combined Pipeline | 640×480 | ~30 | All modules |

---

**Made with ❤️ by Jayadeep / Jay7-Tech**
