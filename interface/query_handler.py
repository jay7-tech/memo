"""
MEMO - Query Handler (Enhanced)
================================
Natural language query processing with expanded pattern support.

Supported Query Types:
    - Location: "where is X", "find X", "locate X", "look for X"
    - Presence: "is X here", "do you see X", "can you see X"
    - Count: "how many X", "count X"
    - Description: "what do you see", "describe the scene"
    - Status: "what's happening", "what is the status"
    - User: "who is here", "who am I"
"""

import re
import time
from datetime import datetime
from typing import Optional, Dict, List, Any


class QueryHandler:
    """
    Handles natural language queries about the scene.
    
    Maintains conversation context for follow-up questions.
    """
    
    def __init__(self):
        """Initialize query handler."""
        # Conversation context
        self.last_object_mentioned: Optional[str] = None
        self.last_query_time = 0
        
        # Object synonyms
        self.synonyms = {
            'water': 'bottle',
            'water bottle': 'bottle',
            'drink': 'bottle',
            'phone': 'cell phone',
            'mobile': 'cell phone',
            'smartphone': 'cell phone',
            'cellphone': 'cell phone',
            'laptop': 'laptop',
            'computer': 'laptop',
            'notebook': 'laptop',
            'cup': 'cup',
            'mug': 'cup',
            'coffee cup': 'cup',
            'keyboard': 'keyboard',
            'keys': 'keyboard',
            'mouse': 'mouse',
            'remote': 'remote',
            'tv remote': 'remote',
            'book': 'book',
            'notebook': 'book',
            'glasses': 'glasses',
            'spectacles': 'glasses',
            'person': 'person',
            'human': 'person',
            'someone': 'person'
        }
    
    def handle_query(self, query_text: str, scene_state) -> Optional[str]:
        """
        Process a natural language query.
        
        Args:
            query_text: User's query text
            scene_state: Current scene state object
        
        Returns:
            Response string or None if not understood
        """
        query = query_text.lower().strip()
        self.last_query_time = time.time()
        
        # Handle pronouns (it, that, the object)
        query = self._resolve_pronouns(query)
        
        # Try each query type
        handlers = [
            self._handle_location,
            self._handle_presence,
            self._handle_count,
            self._handle_description,
            self._handle_status,
            self._handle_user,
        ]
        
        for handler in handlers:
            result = handler(query, scene_state)
            if result:
                return result
        
        return None
    
    def _resolve_pronouns(self, query: str) -> str:
        """Replace pronouns with last mentioned object."""
        if not self.last_object_mentioned:
            return query
        
        pronouns = ['it', 'that', 'the object', 'the thing']
        for pronoun in pronouns:
            if pronoun in query:
                query = query.replace(pronoun, self.last_object_mentioned)
                break
        
        return query
    
    def _normalize_object(self, obj_name: str) -> str:
        """Normalize object name using synonyms."""
        obj_name = obj_name.strip()
        
        # Remove articles
        for article in ['the ', 'a ', 'an ', 'my ', 'your ']:
            if obj_name.startswith(article):
                obj_name = obj_name[len(article):]
        
        # Apply synonyms
        return self.synonyms.get(obj_name, obj_name)
    
    def _find_object(self, obj_name: str, scene_state) -> Optional[Dict]:
        """Find object in scene state with fuzzy matching."""
        obj_name = self._normalize_object(obj_name)
        
        # Exact match
        if obj_name in scene_state.objects:
            return scene_state.objects[obj_name], obj_name
        
        # Partial match
        for key in scene_state.objects.keys():
            if obj_name in key or key in obj_name:
                return scene_state.objects[key], key
        
        return None, obj_name
    
    def _handle_location(self, query: str, scene_state) -> Optional[str]:
        """Handle location queries: where is X, find X, locate X."""
        patterns = [
            r"where (?:is|are) (?:the |my |a )?(.+?)(?:\?|$)",
            r"find (?:the |my |a )?(.+?)(?:\?|$)",
            r"locate (?:the |my |a )?(.+?)(?:\?|$)",
            r"look for (?:the |my |a )?(.+?)(?:\?|$)",
            r"search for (?:the |my |a )?(.+?)(?:\?|$)",
            r"(?:where did|where'd) (?:i put|you see) (?:the |my |a )?(.+?)(?:\?|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                obj_name = match.group(1).strip()
                self.last_object_mentioned = obj_name
                
                obj_data, matched_name = self._find_object(obj_name, scene_state)
                
                if obj_data:
                    position = obj_data.get('position', 'in view')
                    last_seen = obj_data.get('last_seen', 0)
                    diff = time.time() - last_seen
                    
                    if diff < 2.0:
                        return f"I see the {matched_name}. It's {position}."
                    elif diff < 60:
                        return f"The {matched_name} was {position} about {int(diff)} seconds ago."
                    else:
                        time_str = datetime.fromtimestamp(last_seen).strftime('%H:%M')
                        return f"I last saw the {matched_name} at {time_str}, it was {position}."
                else:
                    return f"I haven't seen {obj_name} recently. Let me keep looking."
        
        return None
    
    def _handle_presence(self, query: str, scene_state) -> Optional[str]:
        """Handle presence queries: is X here, do you see X."""
        patterns = [
            r"(?:is|are) (?:there )?(?:the |my |a )?(.+?) (?:here|nearby|around|visible)(?:\?|$)",
            r"(?:do|can) (?:you|u) see (?:the |my |a )?(.+?)(?:\?|$)",
            r"is (?:the |my |a )?(.+?) (?:here|nearby|around|visible)(?:\?|$)",
            r"(?:have you seen|did you see) (?:the |my |a )?(.+?)(?:\?|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                obj_name = match.group(1).strip()
                
                # Handle trailing "here" or "nearby"
                for suffix in [' here', ' nearby', ' around', ' visible']:
                    if obj_name.endswith(suffix):
                        obj_name = obj_name[:-len(suffix)]
                
                self.last_object_mentioned = obj_name
                obj_data, matched_name = self._find_object(obj_name, scene_state)
                
                if obj_data:
                    last_seen = obj_data.get('last_seen', 0)
                    diff = time.time() - last_seen
                    
                    if diff < 5.0:
                        return f"Yes! I can see the {matched_name} right now."
                    else:
                        return f"Not right now. I last saw it {int(diff)} seconds ago."
                else:
                    return f"No, I haven't seen {obj_name}."
        
        return None
    
    def _handle_count(self, query: str, scene_state) -> Optional[str]:
        """Handle count queries: how many X, count X."""
        patterns = [
            r"how many (.+?)(?:\?|$)",
            r"count (?:the )?(.+?)(?:\?|$)",
            r"(?:number of|amount of) (.+?)(?:\?|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                obj_name = match.group(1).strip()
                
                # Remove plural 's' for matching
                singular = obj_name.rstrip('s')
                
                # Count occurrences
                count = 0
                for label in scene_state.objects.keys():
                    if obj_name in label or singular in label:
                        count += 1
                
                if count > 0:
                    return f"I can see {count} {obj_name}."
                else:
                    return f"I don't see any {obj_name} right now."
        
        return None
    
    def _handle_description(self, query: str, scene_state) -> Optional[str]:
        """Handle description queries: what do you see, describe scene."""
        patterns = [
            r"what (?:do|can) you see",
            r"describe (?:the )?(?:scene|room|environment|surroundings)",
            r"what(?:'s| is) (?:in view|visible|around|here)",
            r"what objects",
            r"tell me what you see",
        ]
        
        for pattern in patterns:
            if re.search(pattern, query):
                # Get currently visible objects
                now = time.time()
                visible = []
                
                for label, data in scene_state.objects.items():
                    if now - data.get('last_seen', 0) < 5.0:
                        visible.append(label)
                
                # Add human status
                human_status = ""
                if scene_state.human.get('present'):
                    pose = scene_state.human.get('pose_state', 'unknown')
                    identity = scene_state.human.get('identity')
                    if identity:
                        human_status = f" {identity} is {pose}."
                    else:
                        human_status = f" Someone is {pose}."
                
                if visible:
                    obj_list = ", ".join(visible)
                    return f"I can see: {obj_list}.{human_status}"
                elif human_status:
                    return f"I see a person.{human_status}"
                else:
                    return "I don't see anything specific right now."
        
        return None
    
    def _handle_status(self, query: str, scene_state) -> Optional[str]:
        """Handle status queries: what's happening, status."""
        patterns = [
            r"what(?:'s| is) happening",
            r"(?:what is the |what's the )?status",
            r"how(?:'s| is) (?:it going|everything)",
            r"what(?:'s| is) going on",
        ]
        
        for pattern in patterns:
            if re.search(pattern, query):
                parts = []
                
                # Human status
                if scene_state.human.get('present'):
                    identity = scene_state.human.get('identity', 'Someone')
                    pose = scene_state.human.get('pose_state', 'here')
                    parts.append(f"{identity} is {pose}")
                
                # Focus mode
                if scene_state.focus_mode:
                    parts.append("Focus mode is on")
                
                # Object count
                obj_count = len(scene_state.objects)
                if obj_count > 0:
                    parts.append(f"I'm tracking {obj_count} objects")
                
                if parts:
                    return ". ".join(parts) + "."
                else:
                    return "All systems normal. Nothing specific to report."
        
        return None
    
    def _handle_user(self, query: str, scene_state) -> Optional[str]:
        """Handle user-related queries: who is here, who am I."""
        patterns = [
            (r"who (?:is|are) (?:here|there|present)", "presence"),
            (r"who am i", "identity"),
            (r"do you (?:know|recognize) me", "identity"),
            (r"what(?:'s| is) my name", "identity"),
        ]
        
        for pattern, query_type in patterns:
            if re.search(pattern, query):
                identity = scene_state.human.get('identity')
                present = scene_state.human.get('present', False)
                
                if query_type == "identity":
                    if identity:
                        return f"You are {identity}!"
                    elif present:
                        return "I can see you, but I don't recognize you. Say 'register' followed by your name."
                    else:
                        return "I don't see anyone right now."
                
                elif query_type == "presence":
                    if identity:
                        return f"{identity} is here."
                    elif present:
                        return "Someone is here, but I don't recognize them."
                    else:
                        return "I don't see anyone at the moment."
        
        return None


# Quick test
if __name__ == "__main__":
    class MockSceneState:
        def __init__(self):
            self.objects = {
                'bottle': {'last_seen': time.time(), 'position': 'on the left'},
                'laptop': {'last_seen': time.time() - 30, 'position': 'in the center'},
            }
            self.human = {'present': True, 'identity': 'Jayadeep', 'pose_state': 'sitting'}
            self.focus_mode = False
    
    handler = QueryHandler()
    state = MockSceneState()
    
    test_queries = [
        "where is my bottle?",
        "find the laptop",
        "do you see a phone?",
        "is there a bottle here?",
        "what do you see?",
        "who am I?",
        "how many objects?",
        "what's happening?",
        "where is it?",  # Tests pronoun resolution
    ]
    
    print("Testing QueryHandler:\n")
    for q in test_queries:
        result = handler.handle_query(q, state)
        print(f"Q: {q}")
        print(f"A: {result}\n")
