import os
import time
from google import genai
from google.genai import types

api_key = os.environ["GEMINI_API_KEY"]  # never hard-code keys: this repo is public
client = genai.Client(api_key=api_key)

prompt = "A high-quality, cinematic close-up of a person's hand holding a modern smartphone and scanning a large, colorful QR code displayed on a digital screen. Vibrant indigo and teal lighting. Professional tech event atmosphere."

print(f"Generating teaser scene 1: {prompt}")

try:
    operation = client.models.generate_videos(
        model="veo-3.1-fast-generate-preview",
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution="720p"
        ),
    )

    print("Generation started. Polling for completion...")
    while not operation.done:
        print("Still generating...")
        time.sleep(20)
        operation = client.operations.get(operation)

    if operation.response and operation.response.generated_videos:
        generated_video = operation.response.generated_videos[0]
        # In the new SDK, download might be different. 
        # Checking search result: client.files.download(file=generated_video.video)
        # Actually, the search result shows generated_video.video.save("output_video.mp4")
        video_file = generated_video.video
        video_file.save("_private/marketing/videos/teaser_scene_1.mp4")
        print("Success! Saved to _private/marketing/videos/teaser_scene_1.mp4")
    else:
        print("Generation failed or no video returned.")
        print(f"Operation Response: {operation.response}")

except Exception as e:
    print(f"Error during generation: {e}")
