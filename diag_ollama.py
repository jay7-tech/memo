
import requests
import time
import json

print("\n=== OLLAMA DIAGNOSTIC (V4.7) ===")
url = "http://localhost:11434/api/generate"
model = "tinyllama:latest"

test_prompts = [
    "Q: Who is Elon Musk?\nA:", 
    "Q: Tell me a quick joke.\nA:",
    "Q: Who are you?\nA:"
]

for prompt in test_prompts:
    print(f"\n[Test] Calling: {prompt.strip()}")
    start = time.time()
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 50, "temperature": 0.1}
        }
        resp = requests.post(url, json=payload, timeout=20)
        end = time.time()
        
        if resp.status_code == 200:
            text = resp.json().get('response', '').strip()
            print(f"  Result: {text}")
            print(f"  Time: {end - start:.2f}s")
        else:
            print(f"  Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"  Failed: {e}")

print("\n=== DIAGNOSTIC COMPLETE ===")
