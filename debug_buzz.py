
import sys
import os

# Mock external requests to avoid network deps for this test if needed, 
# but better to test real fetch if possible. 
# For now, let's try to load the personality and run the specific function.

sys.path.append(".")
from core.personality import AIPersonality, init_personality

def test_buzz():
    print("Initializing Personality...")
    ai = init_personality({'backend': 'fallback'}) # Use fallback to test logic flow, or 'ollama' if available
    
    # We want to test the _generate_ollama path specifically if possible, 
    # but we can at least check what get_personalized_updates() returns.
    
    print("\n[Test] Fetching updates...")
    try:
        updates = ai.get_personalized_updates()
        print(f"Updates found: {len(updates)}")
        for u in updates:
            print(f" - {u}")
            
        if not updates:
            print("No updates found. 'buzz' would return static message.")
            return

        print("\n[Test] simulating 'buzz' trigger...")
        # We can't easily reproduce the exact LLM hallucination without the model running,
        # but we can verify the PROMPT processing.
        
        joined_updates = "\n".join(updates)
        summary_prompt = (
            "You are a tech news anchor. Summarize these raw items into a brisk, exciting 3-sentence spoken update.\n"
            "Include:\n"
            "1. One major tech launch or AI news.\n"
            "2. One trending tool or repo.\n"
            "3. One career/internship opportunity if listed.\n\n"
            "Rules:\n"
            "- Answer in ONE paragraph, not a list.\n"
            "- No URLs, no code syntax, no markdown.\n"
            "- Do NOT cut off sentences.\n"
            "- Keep it under 50 words.\n\n"
            f"Raw Data:\n{joined_updates}"
        )
        
        print("\n=== GENERATED PROMPT ===")
        print(summary_prompt)
        print("========================\n")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_buzz()
