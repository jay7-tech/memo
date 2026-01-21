import time
import math

class SceneState:
    def __init__(self):
        # objects: { label: { 'last_seen': float, 'bbox': [x,y,w,h], 'position': str } }
        self.objects = {}
        
        # human: { 'present': bool, 'pose_state': str, 'keypoints': dict, 'last_seen': float }
        self.human = {
            'present': False,
            'pose_state': 'unknown',
            'keypoints': {},
            'last_seen': 0.0,
            'identity': None # 'Jayadeep' or None
        }
        
        # System flags
        self.focus_mode = False 
        self.register_trigger = False
        self.register_name = "User"
        
        self.width = 640 # Default, updated on first frame

    def update(self, detections, pose_data, timestamp, frame_width=640, frame_height=480):
        self.width = frame_width
        
        # 1. Update Objects
        current_labels = set()
        person_detected = False
        
        for det in detections:
            label = det['label']
            if label == 'person':
                person_detected = True
                
            bbox = det['bbox']
            x, y, w, h = bbox
            cx = x + w / 2
            
            if cx < frame_width / 3:
                pos = "left"
            elif cx < 2 * frame_width / 3:
                pos = "center"
            else:
                pos = "right"
            
            self.objects[label] = {
                'last_seen': timestamp,
                'bbox': bbox,
                'position': pos
            }
            current_labels.add(label)

        # 2. Update Human
        # REQUIRE both Pose Data AND Object Detection to agree it's a person
        # This prevents "Ghost" pose detections on chairs/coats from keeping identity alive.
        if pose_data and 'keypoints' in pose_data and person_detected:
            self.human['present'] = True
            self.human['keypoints'] = pose_data['keypoints']
            self.human['last_seen'] = timestamp
            
            # Determine Pose State (Simple Heuristic)
            new_pose = self._determine_pose(pose_data['keypoints'])
            
            # Update pose duration tracking
            current_pose = self.human['pose_state']
            if new_pose != current_pose and new_pose != 'unknown':
                # State changed
                self.human['pose_state'] = new_pose
                self.human['pose_start_time'] = timestamp
            elif 'pose_start_time' not in self.human:
                # Initialize if missing
                self.human['pose_start_time'] = timestamp
                
        else:
            self.human['present'] = False
            self.human['identity'] = None # Reset identity if person leaves
            
            # We keep old keypoints? Or clear? 
            # Prompt says "Human pose changed". If person leaves, 'present' becomes false.
            # We can leave pose_state as last known or set to unknown.
            if timestamp - self.human['last_seen'] > 1.0: # 1 second buffer
                 self.human['pose_state'] = 'unknown'

    def _determine_pose(self, keypoints):
        # Simple heuristic for Sitting vs Standing using vertical relative positions
        # Hip vs Knee.
        # Check if basic leg keypoints exist
        required = ['LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 'LEFT_ANKLE', 'RIGHT_ANKLE']
        
        # MediaPipe names usually: LEFT_HIP, RIGHT_HIP...
        # Let's check available keys.
        
        # Get average hip Y and average knee Y
        try:
            l_ure = keypoints['LEFT_HIP']
            r_ure = keypoints['RIGHT_HIP']
            l_knee = keypoints['LEFT_KNEE']
            r_knee = keypoints['RIGHT_KNEE']
            l_ankle = keypoints['LEFT_ANKLE']
            r_ankle = keypoints['RIGHT_ANKLE']
        except KeyError:
             # If strictly required points missing
             return 'unknown'
        
        # In pixel coords, Y increases downwards.
        # Standing: Hip Y is much smaller (higher) than Knee Y.
        # Sitting: Hip Y is closer to Knee Y vertical level? 
        # Actually more about the angle. 
        # But a simple Y check: 
        # If upper leg is vertical, Standing.
        # If upper leg is horizontal, Sitting.
        
        # Calculate thigh vector projection on Y axis provided we know scale?
        # Easier: Aspect ratio of the leg?
        
        # Simple heuristic: 
        # Compare vertical distance (dy) between Hip and Knee.
        # Compare horizontal distance (dx) between Hip and Knee.
        
        # Average left and right
        hip_y = (l_ure[1] + r_ure[1]) / 2
        knee_y = (l_knee[1] + r_knee[1]) / 2
        hip_x = (l_ure[0] + r_ure[0]) / 2
        knee_x = (l_knee[0] + r_knee[0]) / 2
        
        dy = abs(knee_y - hip_y)
        dx = abs(knee_x - hip_x)
        
        # If thigh is vertical-ish (dy >> dx), standing.
        # If thigh is horizontal-ish (dx > dy * factor), sitting.
        
        if dy > dx * 2:
            return "standing"
        elif dx > dy * 0.5: # Generous threshold for foreshortening
            return "sitting"
        else:
            return "standing" # Default assumption

    def get_object_state(self, label):
        return self.objects.get(label)

    def get_last_seen(self, label):
        obj = self.objects.get(label)
        if obj:
            return obj['last_seen']
        return None
