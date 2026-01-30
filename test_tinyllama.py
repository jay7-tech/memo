
import requests
import time
import json

print("\n=== TESTING TINYLLAMA SPEED ===")
url = "http://localhost:11434/api/generate"
payload = {
    "model": "tinyllama:latest", 
    "prompt": "Say hello and tell me a quick joke about robots.", 
    "stream": False
}

start = time.time()
try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, timeout=30)
    end = time.time()
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n[Response Time]: {end - start:.2f} seconds")
        print(f"[Output]: {data.get('response')}")
    else:
        print(f"Error {response.status_code}: {response.text}")

except Exception as e:
    print(f"Failed: {e}")
