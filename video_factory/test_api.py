import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("ELEVENLABS_API_KEY")
url = "https://api.elevenlabs.io/v1/user"
headers = {"xi-api-key": key}

print(f"Testing API key: {key[:5]}...")
res = requests.get(url, headers=headers)
print(f"Status: {res.status_code}")
print(f"Response: {res.text}")
