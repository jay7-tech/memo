"""
MEMO - Rules Engine Module (Enhanced)
======================================
Event-based reasoning with configurable timings and new features.

Features:
    - Object appearance/disappearance detection
    - Pose state change monitoring (sitting/standing)
    - Focus mode distraction detection
    - Screen proximity alerting
    - Personalized greeting system
    - Posture duration tracking
    - Hydration reminders (NEW)
    - Configurable timings (NEW)

Event Types:
    - "Object appeared: {label}"
    - "Object disappeared: {label}"
    - "TTS: You have been sitting for a while..."
    - "TTS: Put the phone away and focus..."
    - "TTS: You are too close to the screen..."
    - "TTS: Hello {name}. Welcome back."
    - "TTS: Remember to drink some water!" (NEW)
"""

from typing import Dict, List, Set, Any, Optional
import time


class RulesConfig:
    """Configuration for rules engine timings."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        # Posture reminder (seconds)
        self.sitting_reminder = config.get('sitting_reminder', 2700)  # 45 minutes
        self.standing_reminder = config.get('standing_reminder', 1800)  # 30 minutes
        
        # Alert cooldowns (seconds)
        self.focus_cooldown = config.get('focus_cooldown', 10.0)
        self.proximity_cooldown = config.get('proximity_cooldown', 30.0)
        self.hydration_cooldown = config.get('hydration_cooldown', 1800)  # 30 minutes
        
        # Thresholds
        self.proximity_threshold = config.get('proximity_threshold', 0.55)
        self.object_visibility_timeout = config.get('object_visibility_timeout', 0.5)
        self.greeting_reset_time = config.get('greeting_reset_time', 300.0)  # 5 minutes
        
        # Feature toggles
        self.enable_hydration = config.get('enable_hydration', True)
        self.enable_posture = config.get('enable_posture', True)
        self.enable_proximity = config.get('enable_proximity', True)
        self.enable_greetings = config.get('enable_greetings', True)


class RulesEngine:
    """
    Event-based rules engine for MEMO desktop companion.
    
    Analyzes scene state and generates events for TTS responses,
    notifications, and other actions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the RulesEngine.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = RulesConfig(config)
        
        # State tracking
        self.prev_objects: Set[str] = set()
        self.prev_pose_state = 'unknown'
        self.last_check_time = 0
        
        # Debounce timers
        self.last_proximity_alert = 0
        self.last_focus_alert = 0
        self.last_hydration_alert = 0
        self.last_posture_alert = 0
        
        # Greeting tracking
        self.last_greeted_name: Optional[str] = None
        self.last_greeted_time = 0
        
        # Hydration tracking
        self.last_bottle_seen = 0
        self.bottle_interactions = 0
        
        # Rep counting (exercise feature)
        self.rep_count = 0
        self.rep_stage: Optional[str] = None
        self.prev_wrist_y: Optional[float] = None
        self.rep_joint = 'RIGHT_WRIST'
    
    def check_rules(self, scene_state, timestamp: float) -> List[str]:
        """
        Analyze scene state and generate events.
        
        Args:
            scene_state: Current scene state object
            timestamp: Current Unix timestamp
        
        Returns:
            List of event strings (prefix "TTS:" for speech)
        """
        events = []
        
        # 1. Object Appeared / Disappeared
        events.extend(self._check_objects(scene_state, timestamp))
        
        # 2. Posture Monitoring
        if self.config.enable_posture:
            events.extend(self._check_posture(scene_state, timestamp))
        
        # 3. Focus Mode Distraction
        events.extend(self._check_distraction(scene_state, timestamp))
        
        # 4. Hydration Reminder
        if self.config.enable_hydration:
            events.extend(self._check_hydration(scene_state, timestamp))
        
        # 5. Screen Proximity
        if self.config.enable_proximity:
            events.extend(self._check_proximity(scene_state, timestamp))
        
        # 6. Personalized Greeting
        if self.config.enable_greetings:
            events.extend(self._check_greeting(scene_state, timestamp))
        
        self.last_check_time = timestamp
        return events
    
    def _check_objects(self, scene_state, timestamp: float) -> List[str]:
        """Check for object appearance/disappearance."""
        events = []
        
        # Get currently visible objects
        current_visible = set()
        for label, data in scene_state.objects.items():
            if timestamp - data['last_seen'] < self.config.object_visibility_timeout:
                current_visible.add(label)
        
        # New objects
        for obj in current_visible - self.prev_objects:
            events.append(f"Object appeared: {obj}")
        
        # Disappeared objects
        for obj in self.prev_objects - current_visible:
            events.append(f"Object disappeared: {obj}")
        
        self.prev_objects = current_visible
        return events
    
    def _check_posture(self, scene_state, timestamp: float) -> List[str]:
        """Check posture duration and send reminders."""
        events = []
        
        if not scene_state.human['present']:
            self.prev_pose_state = 'unknown'
            return events
        
        current_pose = scene_state.human['pose_state']
        
        # Track pose change
        if current_pose != self.prev_pose_state:
            if self.prev_pose_state != 'unknown' and current_pose != 'unknown':
                # Reset posture timer on change
                self.last_posture_alert = timestamp
            self.prev_pose_state = current_pose
        
        # Check duration
        pose_start = scene_state.human.get('pose_start_time', timestamp)
        duration = timestamp - pose_start
        
        # Cooldown check
        if timestamp - self.last_posture_alert < 60:  # Min 1 minute between alerts
            return events
        
        if current_pose == 'sitting' and duration > self.config.sitting_reminder:
            events.append("TTS: You have been sitting for a while. Time to stretch and move around!")
            self.last_posture_alert = timestamp
            
        elif current_pose == 'standing' and duration > self.config.standing_reminder:
            events.append("TTS: You have been standing for a while. You can take a seat now.")
            self.last_posture_alert = timestamp
        
        return events
    
    def _check_distraction(self, scene_state, timestamp: float) -> List[str]:
        """Check for distractions in focus mode."""
        events = []
        
        if not scene_state.focus_mode:
            return events
        
        # Check for cell phone
        current_visible = set()
        for label, data in scene_state.objects.items():
            if timestamp - data['last_seen'] < 1.0:
                current_visible.add(label)
        
        if 'cell phone' in current_visible:
            if timestamp - self.last_focus_alert > self.config.focus_cooldown:
                events.append("TTS: I see your phone. Put it away and stay focused!")
                self.last_focus_alert = timestamp
        
        return events
    
    def _check_hydration(self, scene_state, timestamp: float) -> List[str]:
        """Check hydration and send water reminders."""
        events = []
        
        # Track bottle visibility
        bottle_visible = False
        for label, data in scene_state.objects.items():
            if 'bottle' in label.lower():
                if timestamp - data['last_seen'] < 2.0:
                    bottle_visible = True
                    # Bottle was interacted with (picked up recently)
                    if timestamp - self.last_bottle_seen > 10.0:
                        self.bottle_interactions += 1
                    self.last_bottle_seen = timestamp
                    break
        
        # If no bottle seen for a while and person is present
        if scene_state.human['present'] and not bottle_visible:
            time_since_bottle = timestamp - self.last_bottle_seen if self.last_bottle_seen > 0 else 0
            
            # Only remind if we've seen the bottle before (user has one)
            if self.last_bottle_seen > 0:
                if time_since_bottle > self.config.hydration_cooldown:
                    if timestamp - self.last_hydration_alert > self.config.hydration_cooldown:
                        events.append("TTS: Don't forget to drink some water! Stay hydrated.")
                        self.last_hydration_alert = timestamp
        
        return events
    
    def _check_proximity(self, scene_state, timestamp: float) -> List[str]:
        """Check if user is too close to screen."""
        events = []
        
        if not scene_state.human['present']:
            return events
        
        kp = scene_state.human.get('keypoints', {})
        width = scene_state.width
        
        proximity_score = 0.0
        
        # Method 1: Shoulder width
        if 'LEFT_SHOULDER' in kp and 'RIGHT_SHOULDER' in kp:
            ls = kp['LEFT_SHOULDER']
            rs = kp['RIGHT_SHOULDER']
            dist = ((ls[0] - rs[0])**2 + (ls[1] - rs[1])**2)**0.5
            proximity_score = dist / width
        
        # Method 2: Ear width (backup)
        elif 'LEFT_EAR' in kp and 'RIGHT_EAR' in kp:
            le = kp['LEFT_EAR']
            re = kp['RIGHT_EAR']
            dist = ((le[0] - re[0])**2 + (le[1] - re[1])**2)**0.5
            proximity_score = (dist / width) * 2.5
        
        # Check threshold
        if proximity_score > self.config.proximity_threshold:
            if timestamp - self.last_proximity_alert > self.config.proximity_cooldown:
                events.append("TTS: You are too close to the screen. Please move back a bit.")
                self.last_proximity_alert = timestamp
        
        return events
    
    def _check_greeting(self, scene_state, timestamp: float) -> List[str]:
        """Check if we should greet a recognized user."""
        events = []
        
        identity = scene_state.human.get('identity')
        
        if identity:
            # New person or different person
            if identity != self.last_greeted_name:
                events.append(f"TTS: Hello {identity}! Welcome back.")
                self.last_greeted_name = identity
                self.last_greeted_time = timestamp
            
            # Re-greet after long absence
            elif timestamp - self.last_greeted_time > self.config.greeting_reset_time:
                if not scene_state.human['present']:
                    # Person just returned
                    events.append(f"TTS: Welcome back, {identity}!")
                    self.last_greeted_time = timestamp
        
        else:
            # Reset if no one present for a while
            if not scene_state.human['present']:
                if timestamp - scene_state.human.get('last_seen', 0) > 5.0:
                    self.last_greeted_name = None
        
        return events
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rule engine statistics."""
        return {
            'objects_tracked': len(self.prev_objects),
            'current_pose': self.prev_pose_state,
            'bottle_interactions': self.bottle_interactions,
            'last_greeted': self.last_greeted_name
        }
    
    def reset(self):
        """Reset all tracking state."""
        self.prev_objects = set()
        self.prev_pose_state = 'unknown'
        self.last_proximity_alert = 0
        self.last_focus_alert = 0
        self.last_hydration_alert = 0
        self.last_posture_alert = 0
        self.last_greeted_name = None
        self.last_greeted_time = 0
        self.last_bottle_seen = 0
        self.bottle_interactions = 0


# Quick test
if __name__ == "__main__":
    # Test with custom config
    config = {
        'sitting_reminder': 60,  # 1 minute for testing
        'hydration_cooldown': 30,  # 30 seconds for testing
        'focus_cooldown': 5
    }
    
    engine = RulesEngine(config)
    print(f"Rules engine initialized with config: {engine.config.__dict__}")
    print(f"Stats: {engine.get_stats()}")
