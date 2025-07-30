import os
import subprocess
import shutil
from mutagen.mp3 import MP3
import argparse
import re
import pathlib
from generate_subs import generate_ass_subtitles, regenerate_ass_from_edited_txt

FFMPEG = "/opt/homebrew/bin/ffmpeg"

def get_audio_duration(audio_path):
    audio = MP3(audio_path)
    return audio.info.length

def generate_clip_commands(images, per_image_duration, temp_dir):
    clips = []
    # Read the existing ken_burns.py template
    template_path = pathlib.Path(__file__).parent / "ken_burns.py"
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    for i, img in enumerate(images):
        out = os.path.join(temp_dir, f"clip_{i}.mp4")
        
        # Create a temporary Manim scene file by replacing placeholders
        scene_content = template_content.replace(
            "{{IMAGE_PATH}}", img
        ).replace(
            "{{RUN_TIME}}", str(per_image_duration)
        )
        
        # Write the temporary scene file
        scene_file = os.path.join(temp_dir, f"scene_{i}.py")
        with open(scene_file, 'w') as f:
            f.write(scene_content)
        
        # Run Manim to generate the clip using the virtual environment's python
        venv_python = str(pathlib.Path(__file__).parent / "env" / "bin" / "python")
        cmd = [
            venv_python, "-m", "manim", "-qh", scene_file, "KenBurnsEffect",
            "--media_dir", temp_dir,
            "--output_file", f"clip_{i}.mp4"
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to generate clip {i} from {img}")
        
        # Find the generated video file in Manim's output structure
        generated_video = os.path.join(temp_dir, "videos", f"scene_{i}", "1920p60", f"clip_{i}.mp4")
        if os.path.exists(generated_video):
            # Copy to our desired output name
            shutil.copy2(generated_video, out)
        else:
            raise RuntimeError(f"Generated video not found at expected location: {generated_video}")
        
        clips.append(out)
    return clips

def build_filter_chain(clips, per_image_duration):
    # Add fade in/out effects with concat filter
    filter_chain = ""
    filter_labels = []
    
    fade_duration = 1.0  # 1.0 seconds for fade in/out (increased from 0.5)
    
    for i in range(len(clips)):
        # Add fade in for first clip, fade out for last clip, and both for middle clips
        if i == 0:  # First clip - fade in only
            filter_chain += f"[{i}:v]fps=30,setpts=PTS-STARTPTS,fade=t=in:st=0:d={fade_duration}[v{i}];"
        elif i == len(clips) - 1:  # Last clip - fade out only
            filter_chain += f"[{i}:v]fps=30,setpts=PTS-STARTPTS,fade=t=out:st={per_image_duration-fade_duration}:d={fade_duration}[v{i}];"
        else:  # Middle clips - fade in and out
            filter_chain += f"[{i}:v]fps=30,setpts=PTS-STARTPTS,fade=t=in:st=0:d={fade_duration},fade=t=out:st={per_image_duration-fade_duration}:d={fade_duration}[v{i}];"
        
        filter_labels.append(f"[v{i}]")
    
    # Use concat filter for smooth transitions
    concat_inputs = "".join(filter_labels)
    filter_chain += f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]"
    
    return filter_chain, "[outv]"

def generate_final_video(clips, audio_path, ass_path, output_path, filter_complex, final_label):
    subtitle_filter = f"ass={ass_path}"
    cmd = [
        FFMPEG, "-y"
    ] + sum([["-i", clip] for clip in clips], []) + [
        "-i", audio_path,
        "-filter_complex", filter_complex + f";{final_label}{subtitle_filter},format=yuv420p[v]",
        "-map", "[v]",
        "-map", f"{len(clips)}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-r", "30",
        "-crf", "18",
        "-shortest",
        output_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError("Failed to generate final video")

def generate_subtitles_only(folder_path):
    """Generate subtitles only without creating video"""
    audio_path = os.path.join(folder_path, "audio.mp3")
    wav_path = os.path.join(folder_path, "audio.wav")
    ass_path = os.path.join(folder_path, "subtitles.ass")
    
    if not os.path.exists(audio_path):
        raise ValueError(f"Audio file not found: {audio_path}")

    # Convert mp3 to wav for Vosk
    if not os.path.exists(wav_path):
        print("Converting MP3 to WAV for speech recognition...")
        subprocess.run([FFMPEG, "-y", "-i", audio_path, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Generating subtitles...")
    generate_ass_subtitles(wav_path, ass_path)
    
    txt_path = ass_path.replace('.ass', '.txt')
    print(f"✅ Subtitles generated:")
    print(f"   ASS file: {ass_path}")
    print(f"   Text file: {txt_path}")
    print(f"\n📖 Review the text file to check subtitle accuracy before making video.")
    print(f"✏️  Edit the text file to fix any errors, then run:")
    print(f"   python make_video.py {folder_path} --mode regenerate-subs")

def regenerate_subtitles_from_edited_txt(folder_path):
    """Regenerate ASS file from edited text file"""
    txt_path = os.path.join(folder_path, "subtitles.txt")
    ass_path = os.path.join(folder_path, "subtitles.ass")
    
    if not os.path.exists(txt_path):
        raise ValueError(f"Text file not found: {txt_path}. Generate subtitles first with --mode subs")
    
    print(f"🔄 Regenerating ASS file from edited text...")
    regenerate_ass_from_edited_txt(txt_path, ass_path)
    print(f"✅ ASS file updated: {ass_path}")
    print(f"🎬 You can now create video with: python make_video.py {folder_path} --mode video")

def create_video_only(folder_path):
    """Create video using existing subtitles"""
    # Validate input files
    images = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path)
                     if f.lower().endswith((".png", ".jpg", ".jpeg"))])
    audio_path = os.path.join(folder_path, "audio.mp3")
    ass_path = os.path.join(folder_path, "subtitles.ass")
    output_filename = os.path.basename(os.path.normpath(folder_path)) + ".mp4"
    output_path = os.path.join(folder_path, output_filename)
    temp_dir = os.path.join(folder_path, "temp_clips")

    if not images:
        raise ValueError(f"No image files found in {folder_path}")
    if not os.path.exists(audio_path):
        raise ValueError(f"Audio file not found: {audio_path}")
    if not os.path.exists(ass_path):
        raise ValueError(f"Subtitle file not found: {ass_path}. Run with --mode subs first.")

    # Create temp directory
    os.makedirs(temp_dir, exist_ok=True)

    try:
        duration = get_audio_duration(audio_path)
        per_image_duration = duration / len(images)

        print(f"Processing {len(images)} images with {per_image_duration:.2f}s per image...")
        print("Using existing subtitles...")
        wav_path = os.path.join(folder_path, "audio.wav")
        print("Generating clips...")
        clips = generate_clip_commands(images, per_image_duration, temp_dir)
        filter_complex, final_label = build_filter_chain(clips, per_image_duration)
        
        print("Generating final video...")
        generate_final_video(clips, audio_path, ass_path, output_path, filter_complex, final_label)

        print(f"✅ Video created at: {output_path}")
        shutil.rmtree(temp_dir)
        os.remove(wav_path)

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        print("🧹 Cleaned up temporary files")

def main(folder_path, mode="full"):
    """
    Main function with different modes:
    - 'full': Generate subtitles and create video (original behavior)
    - 'subs': Generate subtitles only
    - 'video': Create video using existing subtitles
    - 'regenerate-subs': Regenerate ASS file from edited text file
    """
    if mode == "subs":
        generate_subtitles_only(folder_path)
    elif mode == "video":
        create_video_only(folder_path)
    elif mode == "regenerate-subs":
        regenerate_subtitles_from_edited_txt(folder_path)
    else:  # full mode - original behavior
        # Validate input files
        images = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path)
                         if f.lower().endswith((".png", ".jpg", ".jpeg"))])
        audio_path = os.path.join(folder_path, "audio.mp3")
        wav_path = os.path.join(folder_path, "audio.wav")
        output_filename = os.path.basename(os.path.normpath(folder_path)) + ".mp4"
        output_path = os.path.join(folder_path, output_filename)
        temp_dir = os.path.join(folder_path, "temp_clips")
        ass_path = os.path.join(temp_dir, "subtitles.ass")

        if not images:
            raise ValueError(f"No image files found in {folder_path}")
        if not os.path.exists(audio_path):
            raise ValueError(f"Audio file not found: {audio_path}")

        # Convert mp3 to wav for Vosk
        if not os.path.exists(wav_path):
            subprocess.run([FFMPEG, "-y", "-i", audio_path, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Create temp directory
        os.makedirs(temp_dir, exist_ok=True)

        try:
            duration = get_audio_duration(audio_path)
            per_image_duration = duration / len(images)

            print(f"Processing {len(images)} images with {per_image_duration:.2f}s per image...")
            
            # Generate .ass subtitles with word-level highlighting
            print("Generating subtitles...")
            generate_ass_subtitles(wav_path, ass_path)

            print("Generating clips...")
            clips = generate_clip_commands(images, per_image_duration, temp_dir)
            filter_complex, final_label = build_filter_chain(clips, per_image_duration)
            
            print("Generating final video...")
            generate_final_video(clips, audio_path, ass_path, output_path, filter_complex, final_label)

            print(f"✅ Video created at: {output_path}")
            os.remove(wav_path)
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            raise
        finally:
            print("🧹 Cleaned up temporary files")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create video with Ken Burns effect and subtitles")
    parser.add_argument("folder", help="Folder containing images, audio.mp3, and optionally subtitles.ass")
    parser.add_argument("--mode", choices=["full", "subs", "video", "regenerate-subs"], default="full",
                       help="Mode: 'full' (generate subs + video), 'subs' (generate subs only), 'video' (use existing subs), 'regenerate-subs' (regenerate ASS from edited text)")
    
    args = parser.parse_args()
    main(args.folder, args.mode)
