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
        
        # Use a thread pool to manage callback execution without overhead of spawning threads
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        
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
                
                # Execute each callback in the thread pool
                for callback in callbacks:
                    self._executor.submit(self._safe_execute, callback, event)
                    
            except queue.Empty:
                continue
    
    def _safe_execute(self, callback: Callable, event: Event):
        """Safely execute a callback."""
        try:
            callback(event)
        except Exception as e:
            print(f"[EventBus] Callback error: {e}")
    
    def stop(self):
        """Stop the event bus."""
        self._running = False
        self._executor.shutdown(wait=False)
        self._worker.join(timeout=1.0)


class PerformanceMonitor:
    """
    Monitors system resources and adapts processing accordingly.
    
    Optimized for RPi 5:
    - Higher thresholds and better adaptive logic
    """
    
    def __init__(self):
        self.is_raspberry_pi = self._detect_raspberry_pi()
        self.target_fps = 25 if self.is_raspberry_pi else 30
        self.frame_times: List[float] = []
        self.max_samples = 30
        
        # Adaptive parameters - Balanced for Pi 5 power
        self.frame_skip = 3 if self.is_raspberry_pi else 1
        self.detection_interval = 2.0  # Seconds between heavy detections if skipping
        self.face_rec_interval = 5.0
        
        # Resource thresholds (Pi 5 can handle more heat)
        self.cpu_threshold = 75  # Start skipping if CPU > 75%
        self.memory_threshold = 90
    
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


import concurrent.futures

class PerceptionPipeline:
    """
    Unified perception pipeline for efficient inference.
    
    Optimized for RPi 5:
    - Parallel execution via ThreadPoolExecutor
    - Asynchronous face recognition
    - Result caching and lazy initialization
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
        
        # Parallel executor (Separate threads for Detection, Pose, and Face)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        
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
                threshold = self.config.get('face_threshold', 0.6)
                self._face_rec = FaceRecognizer(threshold=threshold)
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
        Process a frame through the perception pipeline in parallel.
        """
        futures = {}
        
        # Start tasks in parallel
        if run_detection:
            self._init_detector()
            futures['detections'] = self.executor.submit(self._detector.detect, frame)
            
        if run_pose:
            self._init_pose()
            futures['pose'] = self.executor.submit(self._pose_estimator.estimate, frame)
            
        if run_face and self._face_rec is not False:
            self._init_face_rec()
            if self._face_rec:
                # Face recognition depends on pose results, but we can attempt it 
                # on the *previous* frame's pose or run it as a follow-on.
                # Here we submit it as a task that will wait if needed.
                # Optimization: Face rec is expensive, run only if person is present.
                futures['identity'] = self.executor.submit(self._async_face_rec, frame)

        # Gather results with timeouts
        results = {
            'detections': self._last_detections,
            'pose': self._last_pose,
            'identity': self._last_identity
        }
        
        try:
            # Each result call is protected by a small timeout
            if 'detections' in futures:
                try:
                    results['detections'] = futures['detections'].result(timeout=0.1)
                    self._last_detections = results['detections']
                except concurrent.futures.TimeoutError:
                    pass
                
            if 'pose' in futures:
                try:
                    results['pose'] = futures['pose'].result(timeout=0.1)
                    self._last_pose = results['pose']
                except concurrent.futures.TimeoutError:
                    pass
                
            if 'identity' in futures:
                try:
                    results['identity'] = futures['identity'].result(timeout=0.01)
                    self._last_identity = results['identity']
                except concurrent.futures.TimeoutError:
                    pass
                    
        except Exception as e:
            # Outer catch for unexpected implementation errors
            print(f"[Perception] Pipeline error: {e}")
            
        return results
    
    def _async_face_rec(self, frame) -> Optional[str]:
        """Helper for parallel face recognition."""
        if self._last_pose:
            return self._recognize_face(frame, self._last_pose)
        return None

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
        
        if self._face_rec:
            return self._face_rec.recognize(frame, [x, y, face_w, face_h])
        return None


class CommandProcessor:
    """
    Centralized command processing with fuzzy pattern matching.
    
    Features:
        - Voice and text command handling
        - Fuzzy matching for natural speech variations
        - Command history
        - Extensible command registry
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.history: List[str] = []
        self.max_history = 50
        
        # Callback for quit
        self.on_quit = None
    
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
            
        # === SHORTHAND COMMANDS (Now available via terminal/dashboard) ===
        if text_lower == 's':
            return self._cmd_selfie(text, context)
        elif text_lower == 'f':
            enabled = not (context['scene_state'].focus_mode if context else False)
            return self._cmd_focus_on(text, context) if enabled else self._cmd_focus_off(text, context)
        elif text_lower == 'v':
            # This is a bit tricky as main.py manages the voice_input instance.
            # We'll publish a system alert so main.py can handle the toggle.
            self.event_bus.publish(Event(EventType.SYSTEM_ALERT, {'action': 'toggle_voice'}))
            return "Toggling voice input..."
        elif text_lower == 'r':
            return self._cmd_register("register User", context)

        # === QUIT / EXIT ===
        quit_patterns = ['quit', 'exit', 'bye', 'goodbye', 'close', 'stop', 'shut down', 'shutdown', 'q']
        for pattern in quit_patterns:
            if text_lower == 'q' or (pattern in text_lower and 'focus' not in text_lower):
                if self.on_quit:
                    self.on_quit()
                return "Goodbye!"
        
        # === FOCUS MODE ON ===
        focus_on_patterns = [
            'focus on', 'focus mode on', 'enable focus', 'start focus',
            'focus enable', 'turn on focus', 'activate focus',
            'focus mode enable', 'distraction on', 'watch me'
        ]
        for pattern in focus_on_patterns:
            if pattern in text_lower:
                return self._cmd_focus_on(text, context)
        
        # === FOCUS MODE OFF ===
        focus_off_patterns = [
            'focus off', 'focus mode off', 'disable focus', 'stop focus',
            'focus disable', 'turn off focus', 'deactivate focus',
            'focus mode disable', 'focus mode of',  # Common misheard
            'off focus', 'no focus', 'end focus', 'focus end',
            'distraction off', 'stop watching'
        ]
        for pattern in focus_off_patterns:
            if pattern in text_lower:
                return self._cmd_focus_off(text, context)
        
        # Check for "focus" + negative word anywhere
        if 'focus' in text_lower:
            negative_words = ['off', 'disable', 'stop', 'end', 'no', 'deactivate', 'of']
            for neg in negative_words:
                if neg in text_lower:
                    return self._cmd_focus_off(text, context)
        
        # === SELFIE / PHOTO ===
        selfie_patterns = [
            'selfie', 'take selfie', 'take a selfie', 'photo', 'take photo',
            'take a photo', 'picture', 'take picture', 'take a picture',
            'capture', 'snap', 'cheese'
        ]
        for pattern in selfie_patterns:
            if pattern in text_lower:
                return self._cmd_selfie(text, context)
        
        # === REGISTER FACE ===
        register_patterns = [
            'register', 'remember me', 'learn my face', 'save my face',
            'add me', 'add my face', 'recognize me', 'learn me'
        ]
        for pattern in register_patterns:
            if pattern in text_lower:
                return self._cmd_register(text, context)
        
        # === VOICE CONTROL ===
        if 'voice' in text_lower and 'on' in text_lower:
            return "Voice is already active since you're speaking to me!"
        if 'voice' in text_lower and ('off' in text_lower or 'stop' in text_lower):
            return "To stop voice, press the V key or type 'voice off'."
        
        # === WHERE IS ===
        if 'where' in text_lower:
            return self._cmd_where_is(text, context)
        
        # === WHAT DO YOU SEE ===
        see_patterns = ['what do you see', 'what can you see', 'what see', 'describe']
        for pattern in see_patterns:
            if pattern in text_lower:
                return self._cmd_what_see(text, context)
        
        # === STATUS ===
        status_patterns = ['status', 'how are you', 'what is happening', "what's happening"]
        for pattern in status_patterns:
            if pattern in text_lower:
                return self._cmd_status(text, context)
        
        # === WHO AM I ===
        if 'who am i' in text_lower or 'who i am' in text_lower:
            return self._cmd_who_am_i(text, context)
        
        # No match - return None for pass-through to query handler
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
        text_clean = text.lower()
        for word in ['register', 'remember', 'learn', 'save', 'add', 'my', 'face', 'me', 'as']:
            text_clean = text_clean.replace(word, '')
        name = text_clean.strip()
        
        if not name or len(name) < 2:
            name = "User"
        
        self.event_bus.publish(Event(
            EventType.SYSTEM_ALERT,
            {'action': 'register_face', 'name': name.title()}
        ))
        return f"Look at the camera, {name.title()}. Registering your face..."
    
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
        obj_name = text.lower()
        for word in ['where', 'is', 'the', 'my', 'a', 'an', 'located', 'find']:
            obj_name = obj_name.replace(word, '')
        obj_name = obj_name.strip()
        
        if not obj_name:
            return "What object are you looking for?"
        
        # Check synonyms
        synonyms = {
            'phone': 'cell phone', 'mobile': 'cell phone',
            'water': 'bottle', 'drink': 'bottle'
        }
        obj_name = synonyms.get(obj_name, obj_name)
        
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
    
    def _cmd_status(self, text: str, context: Dict) -> str:
        if not context or 'scene_state' not in context:
            return "I'm doing well! Systems are running."
        
        scene = context['scene_state']
        parts = []
        
        if scene.focus_mode:
            parts.append("Focus mode is on")
        else:
            parts.append("Focus mode is off")
        
        if scene.human.get('identity'):
            parts.append(f"I see {scene.human['identity']}")
        
        return ". ".join(parts) + "."
    
    def _cmd_who_am_i(self, text: str, context: Dict) -> str:
        if not context or 'scene_state' not in context:
            return "I can't see you right now."
        
        scene = context['scene_state']
        identity = scene.human.get('identity')
        
        if identity:
            return f"You are {identity}!"
        else:
            return "I can see you, but I don't recognize you yet. Say 'remember me' to register."


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
