"""
MEMO - Core Engine (Optimized)
==============================
High-performance core with async processing, adaptive frame skipping,
and resource-aware operation for both Desktop and Raspberry Pi.

Features:
    - Unified perception pipeline
    - Event-driven architecture
    - Adaptive performance tuning
    - Resource monitoring
    - Thread-safe state management
"""

import threading
import time
import queue
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum, auto
import psutil


class EventType(Enum):
    """Event types for the event bus."""
    OBJECT_DETECTED = auto()
    PERSON_ENTERED = auto()
    PERSON_LEFT = auto()
    POSE_CHANGED = auto()
    FACE_RECOGNIZED = auto()
    DISTRACTION_DETECTED = auto()
    VOICE_COMMAND = auto()
    GESTURE_DETECTED = auto()
    FOCUS_MODE_CHANGED = auto()
    SYSTEM_ALERT = auto()


@dataclass
class Event:
    """Event data structure."""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """
    Central event bus for decoupled communication.
    
    Allows modules to publish events and subscribe to specific event types.
    Thread-safe implementation with priority queuing.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue = queue.PriorityQueue()
        self._lock = threading.RLock()
        self._running = True
        self._worker = threading.Thread(target=self._process_events, daemon=True)
        self._worker.start()
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def publish(self, event: Event, priority: int = 5):
        """Publish an event (priority 1-10, lower = higher priority)."""
        self._event_queue.put((priority, time.time(), event))
    
    def _process_events(self):
        """Background worker to process events."""
        while self._running:
            try:
                _, _, event = self._event_queue.get(timeout=0.1)
                with self._lock:
                    callbacks = self._subscribers.get(event.type, [])
                for callback in callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"[EventBus] Callback error: {e}")
            except queue.Empty:
                continue
    
    def stop(self):
        """Stop the event bus."""
        self._running = False
        self._worker.join(timeout=1.0)


class PerformanceMonitor:
    """
    Monitors system resources and adapts processing accordingly.
    
    Features:
        - CPU/Memory monitoring
        - FPS tracking
        - Adaptive frame skipping
        - Raspberry Pi detection
    """
    
    def __init__(self):
        self.is_raspberry_pi = self._detect_raspberry_pi()
        self.target_fps = 10 if self.is_raspberry_pi else 30
        self.frame_times: List[float] = []
        self.max_samples = 30
        
        # Adaptive parameters
        self.frame_skip = 3 if self.is_raspberry_pi else 1
        self.detection_interval = 5.0 if self.is_raspberry_pi else 2.0
        self.face_rec_interval = 3.0 if self.is_raspberry_pi else 1.0
        
        # Resource thresholds
        self.cpu_threshold = 80  # Reduce processing if CPU > 80%
        self.memory_threshold = 85
    
    def _detect_raspberry_pi(self) -> bool:
        """Detect if running on Raspberry Pi."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
        except:
            return False
    
    def record_frame(self):
        """Record frame timestamp for FPS calculation."""
        self.frame_times.append(time.time())
        if len(self.frame_times) > self.max_samples:
            self.frame_times.pop(0)
    
    def get_fps(self) -> float:
        """Calculate current FPS."""
        if len(self.frame_times) < 2:
            return 0.0
        elapsed = self.frame_times[-1] - self.frame_times[0]
        return len(self.frame_times) / elapsed if elapsed > 0 else 0.0
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0)
    
    def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        return psutil.virtual_memory().percent
    
    def should_skip_frame(self, frame_count: int) -> bool:
        """Determine if current frame should be skipped for heavy processing."""
        # Adaptive: increase skip if CPU is high
        cpu = self.get_cpu_usage()
        if cpu > self.cpu_threshold:
            return frame_count % (self.frame_skip * 2) != 0
        return frame_count % self.frame_skip != 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return {
            'fps': round(self.get_fps(), 1),
            'cpu': round(self.get_cpu_usage(), 1),
            'memory': round(self.get_memory_usage(), 1),
            'frame_skip': self.frame_skip,
            'is_pi': self.is_raspberry_pi
        }


class PerceptionPipeline:
    """
    Unified perception pipeline for efficient inference.
    
    Features:
        - Single-pass object + pose detection
        - Async face recognition
        - Result caching
        - Warmup on init
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Cached results
        self._last_detections = []
        self._last_pose = None
        self._last_identity = None
        
        # Lazy loading flags
        self._detector = None
        self._pose_estimator = None
        self._face_rec = None
        
        # Timing
        self._last_detection_time = 0
        self._last_face_time = 0
    
    def _init_detector(self):
        """Lazy init object detector."""
        if self._detector is None:
            from perception import ObjectDetector
            model = self.config.get('yolo_model', 'yolov8n.pt')
            self._detector = ObjectDetector(model)
            print("[Perception] Object detector initialized")
    
    def _init_pose(self):
        """Lazy init pose estimator."""
        if self._pose_estimator is None:
            from perception import PoseEstimator
            self._pose_estimator = PoseEstimator()
            print("[Perception] Pose estimator initialized")
    
    def _init_face_rec(self):
        """Lazy init face recognition."""
        if self._face_rec is None:
            try:
                from perception.face_rec import FaceRecognizer
                self._face_rec = FaceRecognizer()
                print("[Perception] Face recognition initialized")
            except Exception as e:
                print(f"[Perception] Face rec unavailable: {e}")
                self._face_rec = False  # Mark as unavailable
    
    def warmup(self, frame):
        """Warm up models with a sample frame."""
        print("[Perception] Warming up models...")
        self._init_detector()
        self._init_pose()
        
        # Run inference once to warm up GPU/CPU caches
        if frame is not None:
            self._detector.detect(frame)
            self._pose_estimator.estimate(frame)
        
        print("[Perception] Warmup complete")
    
    def process(self, frame, run_detection=True, run_pose=True, run_face=False) -> Dict[str, Any]:
        """
        Process a frame through the perception pipeline.
        
        Args:
            frame: BGR image from OpenCV
            run_detection: Run object detection
            run_pose: Run pose estimation
            run_face: Run face recognition
        
        Returns:
            Dict with 'detections', 'pose', 'identity' keys
        """
        result = {
            'detections': self._last_detections,
            'pose': self._last_pose,
            'identity': self._last_identity
        }
        
        with self._lock:
            if run_detection:
                self._init_detector()
                self._last_detections = self._detector.detect(frame)
                result['detections'] = self._last_detections
            
            if run_pose:
                self._init_pose()
                self._last_pose = self._pose_estimator.estimate(frame)
                result['pose'] = self._last_pose
            
            if run_face and self._face_rec is not False:
                self._init_face_rec()
                if self._face_rec and result['pose']:
                    identity = self._recognize_face(frame, result['pose'])
                    if identity:
                        self._last_identity = identity
                        result['identity'] = identity
        
        return result
    
    def _recognize_face(self, frame, pose_data) -> Optional[str]:
        """Extract face from pose keypoints and recognize."""
        if not pose_data or 'keypoints' not in pose_data:
            return None
        
        kp = pose_data['keypoints']
        if 'NOSE' not in kp:
            return None
        
        # Construct face bounding box from keypoints
        nose = kp['NOSE']
        
        # Use ear distance for face width if available
        if 'LEFT_EAR' in kp and 'RIGHT_EAR' in kp:
            l_ear = kp['LEFT_EAR']
            r_ear = kp['RIGHT_EAR']
            ear_dist = abs(l_ear[0] - r_ear[0])
            face_w = int(ear_dist * 2.0)
        else:
            face_w = 150  # Default face width
        
        face_h = int(face_w * 1.2)
        x = int(nose[0]) - face_w // 2
        y = int(nose[1]) - face_h // 2
        
        return self._face_rec.recognize(frame, [x, y, face_w, face_h])


class CommandProcessor:
    """
    Centralized command processing with pattern matching.
    
    Features:
        - Voice and text command handling
        - Fuzzy matching for commands
        - Command history
        - Extensible command registry
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.commands: Dict[str, Callable] = {}
        self.history: List[str] = []
        self.max_history = 50
        
        # Register default commands
        self._register_defaults()
    
    def _register_defaults(self):
        """Register built-in commands."""
        self.register('focus on', self._cmd_focus_on)
        self.register('focus off', self._cmd_focus_off)
        self.register('register', self._cmd_register)
        self.register('selfie', self._cmd_selfie)
        self.register('photo', self._cmd_selfie)
        self.register('where is', self._cmd_where_is)
        self.register('what do you see', self._cmd_what_see)
    
    def register(self, pattern: str, handler: Callable):
        """Register a command pattern and handler."""
        self.commands[pattern.lower()] = handler
    
    def process(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        Process a text command.
        
        Args:
            text: Command text
            context: Additional context (scene_state, etc.)
        
        Returns:
            Response string or None
        """
        text_lower = text.strip().lower()
        self.history.append(text)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Exact match first
        for pattern, handler in self.commands.items():
            if pattern in text_lower:
                return handler(text, context)
        
        # No match - return None for pass-through to LLM
        return None
    
    def _cmd_focus_on(self, text: str, context: Dict) -> str:
        self.event_bus.publish(Event(
            EventType.FOCUS_MODE_CHANGED,
            {'enabled': True}
        ))
        return "Focus mode enabled. I will watch for distractions."
    
    def _cmd_focus_off(self, text: str, context: Dict) -> str:
        self.event_bus.publish(Event(
            EventType.FOCUS_MODE_CHANGED,
            {'enabled': False}
        ))
        return "Focus mode disabled."
    
    def _cmd_register(self, text: str, context: Dict) -> str:
        # Extract name if provided
        name = text.lower().replace('register', '').replace('me', '').strip()
        if not name:
            name = "User"
        
        self.event_bus.publish(Event(
            EventType.SYSTEM_ALERT,
            {'action': 'register_face', 'name': name}
        ))
        return f"Look at the camera, {name}. Registering your face..."
    
    def _cmd_selfie(self, text: str, context: Dict) -> str:
        self.event_bus.publish(Event(
            EventType.SYSTEM_ALERT,
            {'action': 'selfie'}
        ))
        return "Say cheese!"
    
    def _cmd_where_is(self, text: str, context: Dict) -> str:
        if not context or 'scene_state' not in context:
            return "I'm not sure. Can't access scene data."
        
        scene = context['scene_state']
        # Extract object name
        obj_name = text.lower().replace('where is', '').replace('the', '').strip()
        
        obj_state = scene.get_object_state(obj_name)
        if obj_state:
            pos = obj_state.get('position', 'unknown')
            last_seen = obj_state.get('last_seen', 0)
            age = time.time() - last_seen
            
            if age < 5:
                return f"The {obj_name} is on the {pos} side."
            else:
                return f"I last saw the {obj_name} on the {pos} side, {int(age)} seconds ago."
        
        return f"I don't see a {obj_name} right now."
    
    def _cmd_what_see(self, text: str, context: Dict) -> str:
        if not context or 'scene_state' not in context:
            return "I can't see anything right now."
        
        scene = context['scene_state']
        objects = list(scene.objects.keys())
        
        if not objects:
            return "I don't see any objects right now."
        
        if 'person' in objects:
            objects.remove('person')
            prefix = "I see you, and also "
        else:
            prefix = "I see "
        
        if not objects:
            return "I see you!"
        
        return prefix + ", ".join(objects) + "."


# Global instances for easy access
_event_bus: Optional[EventBus] = None
_perf_monitor: Optional[PerformanceMonitor] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_perf_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor."""
    global _perf_monitor
    if _perf_monitor is None:
        _perf_monitor = PerformanceMonitor()
    return _perf_monitor
