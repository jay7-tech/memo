
class MockState:
    def __init__(self):
        self.pending_commands = MockQueue()
        self.focus_mode = False
        self.voice_active = True
        self.pending_commands.put("idle")

class MockQueue:
    def __init__(self):
        self.items = []
    def empty(self):
        return len(self.items) == 0
    def get_nowait(self):
        return self.items.pop(0)
    def put(self, item):
        self.items.append(item)

def process_cmd(cmd):
    cmd = str(cmd).strip().lower()
    print(f"DEBUG: Processing '{cmd}'")
    
    if cmd == 'idle':
        print("SUCCESS: Idle caught")
        return True
    return False

# Test
print("\n--- Test 1: Clean 'idle' ---")
process_cmd("idle")

print("\n--- Test 2: Dirty 'idle ' ---")
process_cmd("idle ")

print("\n--- Test 3: Uppercase 'IDLE' ---")
process_cmd("IDLE")
