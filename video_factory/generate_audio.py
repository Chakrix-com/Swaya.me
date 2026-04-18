import os
import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" - Professional & Clear

SCENES = {
    "scene1": "You've been there. A presentation where everyone is looking at their phones instead of you. What if you could turn that distraction into action?",
    "scene2": "Meet Swaya.me. The interactive platform for modern teams, teachers, and creators. Host live quizzes, run async exams, or simple polls—all in one place.",
    "scene3": "Create in seconds with AI assistance. And the magic? Zero friction. No apps to download. No logins for your audience. Just scan, join, and play.",
    "scene4": "Watch the energy in the room shift. From a team of ten to a stadium of ten thousand, Swaya.me scales with you in real-time.",
    "scene5": "Language shouldn't be a barrier. With support for 11 global languages, Swaya.me ensures every voice is heard, anywhere on earth.",
    "scene6": "Export your results to PDF, Excel, or PowerPoint instantly. Host your first session for free today at Swaya dot me."
}

def generate_audio(scene_id, text, output_dir="assets/audio/en"):
    os.makedirs(output_dir, exist_ok=True)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    print(f"Generating audio for {scene_id}...")
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(f"{output_dir}/{scene_id}.mp3", "wb") as f:
                f.write(response.content)
            print(f"Saved to {output_dir}/{scene_id}.mp3")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed for {scene_id}: {e}")

if __name__ == "__main__":
    for scene_id, text in SCENES.items():
        generate_audio(scene_id, text)
