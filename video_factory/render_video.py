import os
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
from moviepy.config import change_settings
import PIL.Image

# Patch for Pillow 10+ compatibility with MoviePy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Configure local FFmpeg
FFMPEG_BINARY = os.path.abspath("bin/ffmpeg")
change_settings({"FFMPEG_BINARY": FFMPEG_BINARY})

def create_scene(image_path, audio_path, duration, text=None):
    # Load image and set duration
    img_clip = ImageClip(image_path).set_duration(duration)
    
    # Apply Ken Burns Effect (Simple Zoom)
    # Start at 1.0 scale, end at 1.1 scale
    img_clip = img_clip.resize(lambda t: 1 + 0.05 * t/duration)
    
    # Load audio
    audio_clip = AudioFileClip(audio_path)
    img_clip = img_clip.set_audio(audio_clip)
    
    # Optional: Add text overlay (requires ImageMagick or manual Pilllow/OpenCV rendering)
    # For now, we'll keep it clean with just the high-res screenshots
    
    return img_clip

def assemble_video(output_name="swaya_explainer_en.mp4"):
    scenes = []
    asset_dir = "assets"
    audio_dir = "assets/audio/en"
    
    scene_config = [
        ("scene1_dashboard.png", "scene1.mp3"),
        ("scene2_modes.png", "scene2.mp3"),
        ("scene3_aigen.png", "scene3.mp3"),
        ("scene4_live.png", "scene4.mp3"),
        ("scene5_languages.png", "scene5.mp3"),
        ("scene6_export.png", "scene6.mp3"),
    ]
    
    for img_name, audio_name in scene_config:
        img_path = os.path.join(asset_dir, img_name)
        audio_path = os.path.join(audio_dir, audio_name)
        
        if os.path.exists(img_path) and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            scenes.append(create_scene(img_path, audio_path, audio_clip.duration))
        else:
            print(f"Warning: Missing assets for {img_name} or {audio_name}")

    if not scenes:
        print("Error: No scenes to assemble!")
        return

    # Concatenate all scenes
    final_video = concatenate_videoclips(scenes, method="compose")
    
    # Add Logo Overlay
    logo_path = os.path.join(asset_dir, "logo.png")
    if os.path.exists(logo_path):
        logo = (ImageClip(logo_path)
                .set_duration(final_video.duration)
                .resize(height=80) 
                .set_pos(("left", "top"))
                .margin(left=20, top=20, opacity=0)
                .set_opacity(0.8))
        final_video = CompositeVideoClip([final_video, logo])

    # Write output
    print(f"Rendering final video: {output_name}...")
    final_video.write_videofile(output_name, fps=24, codec="libx264", audio_codec="aac")

if __name__ == "__main__":
    assemble_video()
