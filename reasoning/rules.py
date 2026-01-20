class RulesEngine:
    def __init__(self):
        self.prev_objects = set()
        self.prev_pose_state = 'unknown'
        self.last_check_time = 0
        
        # Rep Counting
        self.rep_count = 0
        self.rep_stage = None # 'up' or 'down'
        self.prev_wrist_y = None
        self.rep_joint = 'RIGHT_WRIST' # Default to tracking right wrist
        
        self.last_proximity_alert = 0
        self.last_greeted_name = None
        self.last_greeted_time = 0
    
    def check_rules(self, scene_state, timestamp):
        events = []
        
        # 1. Object Appeared / Disappeared
        # Current present objects (recently seen, e.g. < 0.5s ago)
        # However, SceneState stores ALL objects ever seen?
        # SceneState logic I wrote keeps them in dict.
        # I need to check `last_seen` vs `timestamp`.
        
        current_visible_objects = set()
        for label, data in scene_state.objects.items():
            if timestamp - data['last_seen'] < 0.5: # 500ms threshold
                current_visible_objects.add(label)
        
        # Appeared
        new_objects = current_visible_objects - self.prev_objects
        for obj in new_objects:
            events.append(f"Object appeared: {obj}")
            
        # Disappeared
        # Only trigger if it was present previously and now isn't.
        # And we use a timeout. The loop above handles "current visibility".
        # So diff set is enough.
        missing_objects = self.prev_objects - current_visible_objects
        for obj in missing_objects:
            events.append(f"Object disappeared: {obj}")
            
        self.prev_objects = current_visible_objects
        
        # 2. Pose Changed & Duration Check
        current_pose = scene_state.human['pose_state']
        
        if scene_state.human['present']:
            if current_pose != self.prev_pose_state and self.prev_pose_state != 'unknown' and current_pose != 'unknown':
               # events.append(f"Human pose changed: {self.prev_pose_state} -> {current_pose}")
               pass # Reduce spam
               
            self.prev_pose_state = current_pose
            
            # Duration Check (Feature 1)
            if 'pose_start_time' in scene_state.human and scene_state.focus_mode: # Only nag in focus mode? Or always? Let's say always for health.
                duration = timestamp - scene_state.human['pose_start_time']
                # Alert every X seconds (e.g., 45 mins = 2700s)
                # Demo: 60s
                
                demo_threshold = 60 # seconds
                if duration > demo_threshold and int(duration) % 30 == 0: 
                    if current_pose == 'sitting':
                        events.append("TTS: You have been sitting for a while. It is time to stretch.")
                    elif current_pose == 'standing':
                        events.append("TTS: You have been standing for a while. You can sit now.")

        else:
            self.prev_pose_state = 'unknown'
            
        # 3. Distraction Detection (Feature 3)
        # Check if 'cell phone' is in visible objects
        # ONLY IN FOCUS MODE
        if scene_state.focus_mode and 'cell phone' in current_visible_objects:
             # Trigger faster
             events.append("TTS: Put the phone away and focus on your work!")

        # 4. Hydration Helper (Feature 7)
        # Track 'bottle' movement?
        if 'bottle' in scene_state.objects:
            # We need to track 'last_moved_time' for bottle? 
            # Complex for MVP. Simple check: 'bottle' seen recently?
            # Or just periodic reminder if bottle IS present.
            pass
            
        # 5. Screen Proximity Alert (Leaning too close)
        if scene_state.human['present']:
            kp = scene_state.human['keypoints']
            width = scene_state.width
            
            # Metric 1: Shoulder Width
            proximity_score = 0.0
            
            if 'LEFT_SHOULDER' in kp and 'RIGHT_SHOULDER' in kp:
                ls = kp['LEFT_SHOULDER']
                rs = kp['RIGHT_SHOULDER']
                # Euclidian distance roughly since mostly horizontal
                dist = ((ls[0]-rs[0])**2 + (ls[1]-rs[1])**2)**0.5
                proximity_score = dist / width
                
            # Metric 2: Eye/Ear Width (Backup if shoulders cut off but head visible)
            elif 'LEFT_EAR' in kp and 'RIGHT_EAR' in kp:
                le = kp['LEFT_EAR']
                re = kp['RIGHT_EAR']
                dist = ((le[0]-re[0])**2 + (le[1]-re[1])**2)**0.5
                # Ears are closer than shoulders, so threshold adjustment needed
                proximity_score = (dist / width) * 2.5 # Approximate shoulder-to-ear ratio
                
            # Threshold Check
            # If shoulders take up > 50% of the screen width, you're quite close.
            # > 60% is very close.
            if proximity_score > 0.55:
                 # Debounce: Only alert every 15 seconds
                     events.append("TTS: You are too close to the screen. Please move back.")
                     self.last_proximity_alert = timestamp
        
        # 6. Greeting Rule
        # If identity is detected and wasn't before
        if scene_state.human['identity']:
            name = scene_state.human['identity']
            # We need to track 'last_greeted_name' or similar to avoid spam
            # Simple logic: If we haven't greeted this name in 1 hour?
            # For MVP: Just once per session or if absent for long time?
            # Let's use a "last_greeted" timestamp in RulesEngine
            
            if name != self.last_greeted_name: # New person or first time
                 events.append(f"TTS: Hello {name}. Welcome back.")
                 self.last_greeted_name = name
                 self.last_greeted_time = timestamp
            elif timestamp - self.last_greeted_time > 300: # Re-greet after 5 mins absence?
                 # Need to check absence. 
                 # If human.present was False for X mins, then re-greet.
                 pass
                 
        else:
             # Reset greet if no one is there?
             if not scene_state.human['present']:
                 # If absent for > 5 seconds, reset name so we greet again
                 if timestamp - scene_state.human['last_seen'] > 5.0:
                     self.last_greeted_name = None
                 
        return events
