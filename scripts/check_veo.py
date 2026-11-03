from google import genai
import os

api_key = os.environ["GEMINI_API_KEY"]  # never hard-code keys: this repo is public
client = genai.Client(api_key=api_key)

print("Checking available models...")
try:
    models = client.models.list()
    for m in models:
        print(f"Model: {m.name}, Supported Actions: {m.supported_actions}")
except Exception as e:
    print(f"Error: {e}")
