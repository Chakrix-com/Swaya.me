import os
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, clips_array
from moviepy.config import change_settings
import PIL.Image

# Patch for Pillow 10+ compatibility with MoviePy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Configure local FFmpeg
FFMPEG_BINARY = os.path.abspath("bin/ffmpeg")
change_settings({"FFMPEG_BINARY": FFMPEG_BINARY})

def create_side_by_side(host_img, part_img, duration):
    # Load and resize for 1920x1080 canvas
    # Each side will be 960x1080
    host_clip = ImageClip(host_img).set_duration(duration)
    part_clip = ImageClip(part_img).set_duration(duration)
    
    # Crop to 16:9 vertical slivers or just resize to fit?
    # Better: Resize to fit 960 width while maintaining ratio, black bars if needed
    host_clip = host_clip.resize(width=960)
    part_clip = part_clip.resize(width=960)
    
    # Combine horizontally
    combined = clips_array([[host_clip, part_clip]])
    
    # Subtle zoom on the whole combined clip
    combined = combined.resize(lambda t: 1 + 0.03 * t/duration)
    
    return combined

def create_scene(image_path, audio_path, duration):
    img_clip = ImageClip(image_path).set_duration(duration)
    # Simple zoom
    img_clip = img_clip.resize(lambda t: 1 + 0.05 * t/duration)
    # Set audio
    audio_clip = AudioFileClip(audio_path)
    return img_clip.set_audio(audio_clip)

def create_multi_shot_scene(assets, audio_path, output_path):
    # assets can be a list of (image_or_pair, duration_weight)
    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration
    
    # Calculate absolute durations from weights
    total_weight = sum(a[1] for a in assets)
    clips = []
    
    asset_dir = "assets"
    
    for asset, weight in assets:
        duration = (weight / total_weight) * total_duration
        if isinstance(asset, tuple):
            h_path = os.path.join(asset_dir, asset[0])
            p_path = os.path.join(asset_dir, asset[1])
            # Each side resized to fit 960x1080
            h_clip = ImageClip(h_path).set_duration(duration).resize(width=960)
            p_clip = ImageClip(p_path).set_duration(duration).resize(width=960)
            clip = clips_array([[h_clip, p_clip]])
        else:
            img_path = os.path.join(asset_dir, asset)
            clip = ImageClip(img_path).set_duration(duration)
            # Resize to fit 1920 height/width while maintaining ratio
            clip = clip.resize(width=1920) if clip.w/clip.h > 16/9 else clip.resize(height=1080)
            
        # Add subtle zoom to every sub-clip
        clip = clip.resize(lambda t: 1 + 0.04 * t/duration)
        clips.append(clip)
        
    # Standardize result to 1920x1080
    combined_view = concatenate_videoclips(clips, method="compose")
    
    # Force 1920x1080 canvas
    final_view = CompositeVideoClip([combined_view.set_pos("center")], size=(1920, 1080))
    final_view = final_view.set_audio(audio_clip)
    
    # Add Logo small
    logo_path = os.path.join(asset_dir, "logo.png")
    if os.path.exists(logo_path):
        logo = (ImageClip(logo_path)
                .set_duration(final_view.duration)
                .resize(height=50)
                .set_pos(("right", "bottom"))
                .margin(right=15, bottom=15, opacity=0)
                .set_opacity(0.8))
        final_view = CompositeVideoClip([final_view, logo])
        
    print(f"Rendering standard 1080p segment: {output_path}...")
    final_view.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", bitrate="5000k")

def assemble_segmented_video():
    os.makedirs("segments", exist_ok=True)
    # Clean up old segments
    os.system("rm -f segments/*.mp4")
    
    # Engagement Overdrive Config
    # Format: (assets, audio_path or None for silent shots)
    master_config = [
        # Intro Animation (4s Silent)
        ([("intro_card.png", 1)], None),
        # 1. Intro Voice
        ([("scene1_dashboard.png", 10), ("scene2_modes.png", 5), ("scene1_dashboard.png", 10)], "scene1.mp3"),
        # 2. Modes
        ([("scene2_modes.png", 1), ("scene4_live.png", 1)], "scene2.mp3"),
        # 3. Quiz (Join -> MCQ)
        ([(("h_join.png", "p_join.png"), 1), (("h_quiz.png", "p_quiz.png"), 1)], "scene3.mp3"),
        # 4. Poll (Host WC -> Mobile typing)
        ([("p_wordcloud.png", 1), (("h_wordcloud.png", "p_wordcloud.png"), 2)], "scene4.mp3"),
        # 5. Exam (Host stats -> Mobile timer -> Offline QR)
        ([("exam_host.png", 1), ("exam_mobile.png", 1), ("offline_qr.png", 1)], "scene5.mp3"),
        # 6. AI (Prompt -> Progress -> Result)
        ([("ai_prompt.png", 1), ("ai_progress.png", 1), ("scene3_aigen.png", 1)], "scene6.mp3"),
        # 7. Scale
        ([("scene4_live.png", 1), ("scene5_languages.png", 1)], "scene7.mp3"),
        # 8. Export
        ([("scene6_export.png", 1)], "scene8.mp3"),
        # Outro Animation (6s Silent)
        ([("outro_card.png", 1)], None),
    ]
    
    for i, (assets, audio_name) in enumerate(master_config, 1):
        output_path = f"segments/segment{i}.mp4"
        if audio_name:
            audio_path = f"assets/audio/en/{audio_name}"
            if os.path.exists(audio_path):
                create_multi_shot_scene(assets, audio_path, output_path)
        else:
            # Silent Title Card (Intro/Outro)
            duration = 4 if i == 1 else 6
            clips = []
            for asset, weight in assets:
                img_path = os.path.join("assets", asset)
                clip = ImageClip(img_path).set_duration(duration)
                # Subtle zoom and fade in
                clip = clip.resize(lambda t: 1 + 0.05 * t/duration).fadein(1.0)
                clips.append(clip)
            final_view = concatenate_videoclips(clips, method="compose")
            final_view = CompositeVideoClip([final_view.set_pos("center")], size=(1920, 1080))
            
            # Add silent audio track for concat compatibility
            from moviepy.audio.AudioClip import AudioClip
            import numpy as np
            make_frame = lambda t: np.zeros((2, 44100 // 24)) # Dummy silence
            # Actually simpler for MoviePy:
            silence = AudioClip(lambda t: [0, 0], duration=duration, fps=44100)
            final_view = final_view.set_audio(silence)
            
            print(f"Rendering title segment with silence: {output_path}...")
            final_view.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", bitrate="5000k")
            
    # Final Join using FFmpeg
    with open("segments/list.txt", "w") as f:
        for i in range(1, len(master_config) + 1):
            if os.path.exists(f"segments/segment{i}.mp4"):
                f.write(f"file 'segment{i}.mp4'\n")
            
    print("Stitching cinematic masterpiece with FFmpeg...")
    os.system(f"{FFMPEG_BINARY} -f concat -safe 0 -i segments/list.txt -c copy swaya_masterpiece_en.mp4 -y")

if __name__ == "__main__":
    assemble_segmented_video()
