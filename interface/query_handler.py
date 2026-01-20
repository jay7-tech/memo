import re
import time
from datetime import datetime

class QueryHandler:
    def __init__(self):
        pass

    def handle_query(self, query_text, scene_state):
        """
        Parses query and returns response string.
        Returns None if query not understood or irrelevant.
        """
        query_text = query_text.lower().strip()
        
        # Regex for "Where is <object>?"
        match = re.search(r"where is (.+)\??", query_text)
        if match:
            obj_name = match.group(1).strip()
            # Remove determiners "the", "a"
            if obj_name.startswith("the "):
                obj_name = obj_name[4:]
            elif obj_name.startswith("a "):
                obj_name = obj_name[2:]
            
            # Lookup in state
            # Assuming keys are consistent with query. 
            # YOLO labels usually lowercase, e.g., 'bottle'.
            
            # Try exact match
            obj_data = scene_state.objects.get(obj_name)
            
            # If not found, try partial match or fuzzy?
            if not obj_data:
                # Basic linear search for keys
                found_key = None
                for key in scene_state.objects.keys():
                    if obj_name in key or key in obj_name:
                        found_key = key
                        break
                if found_key:
                    obj_data = scene_state.objects[found_key]
                    obj_name = found_key # Use the actual detected name
            
            if obj_data:
                bbox = obj_data['bbox']
                position = obj_data['position']
                last_seen = obj_data['last_seen']
                
                now = time.time()
                diff = now - last_seen
                
                time_str = datetime.fromtimestamp(last_seen).strftime('%H:%M:%S')
                
                if diff < 1.0:
                    return f"{obj_name} is currently {position}, seen just now."
                elif diff < 60:
                     return f"{obj_name} was seen {int(diff)} seconds ago at {position}."
                else:
                    return f"{obj_name} was last seen at {time_str} at {position}."
            else:
                return f"I haven't seen {obj_name} recently."

        # Regex for "Is [object] here?", "Do you/u see [object]?", "Can you see..."
        match_bool = re.search(r"(is|do (you|u) see|can (you|u) see) (.+)( here| nearby)?\??", query_text)
        if match_bool:
            # Extract object name (Group 4 because of nested groups in regex)
            # 1: (is|do (you|u) see|can (you|u) see)
            # 2: (you|u) or None inside group 1
            # 3: (you|u) or None inside group 1
            # Wait, let's count:
            # (is|do (you|u) see|can (you|u) see) -> Group 1
            # Group 1 contains nested groups. 
            # Example "do u see": Group 1="do u see", Group 2="u"
            # Example "can you see": Group 1="can you see", Group 3="you"
            # The (.+) is Group 4.
            obj_name = match_bool.group(4).strip()
             # Cleanup "my", "the"
            if obj_name.startswith("my "): obj_name = obj_name[3:]
            elif obj_name.startswith("the "): obj_name = obj_name[4:]
            
            # Remove " here" or " nearby" if caught in group 2 (regex dependent)
            obj_name = obj_name.replace(" here", "").replace(" nearby", "")

            # Synonyms
            if obj_name in ['water', 'water bottle', 'drink']:
                obj_name = 'bottle'
            elif obj_name in ['phone', 'mobile', 'smartphone']:
                obj_name = 'cell phone'
            
            # Check presence
            obj_data = scene_state.objects.get(obj_name)
            
            # Fuzzy match fallback
            if not obj_data:
                for key in scene_state.objects.keys():
                    if obj_name in key or key in obj_name:
                        obj_data = scene_state.objects[key]
                        break
            
            if obj_data:
                 last_seen = obj_data['last_seen']
                 if time.time() - last_seen < 5.0:
                     return f"Yes, I see the {obj_name}."
                 else:
                     return f"No, I don't see the {obj_name} right now (last seen {int(time.time()-last_seen)}s ago)."
            else:
                return f"No, I haven't seen {obj_name}."
        
        return None
