import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')

print(f"--- Gemini Diagnostics ---")
if not api_key:
    print("ERROR: No GEMINI_API_KEY found in .env variable.")
    sys.exit(1)

print(f"API Key found: {api_key[:10]}********")

try:
    print("\nAttempting to connect with 'google-genai' (New SDK)...")
    from google import genai
    client = genai.Client(api_key=api_key)
    
    print("Listing available models (this verifies the key works)...")
    models = list(client.models.list())
    
    print(f"Found {len(models)} models.")
    for m in models:
        # Filter for generateContent supported models
        if 'generateContent' in m.supported_actions:
            print(f" [AVAILABLE] {m.name} ({m.display_name})")
        else:
             print(f" [OTHER] {m.name}")

    print("\nTest Generation with 'gemini-1.5-flash':")
    try:
        response = client.models.generate_content(model='gemini-1.5-flash', contents='Hello')
        print(f"SUCCESS: {response.text}")
    except Exception as e:
        print(f"GENERATION FAILED: {e}")

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    print("Possibilities:")
    print("1. API Key is invalid.")
    print("2. 'Generative Language API' is not enabled in Google Cloud Console.")
    print("3. Billing is disabled for this project.")
