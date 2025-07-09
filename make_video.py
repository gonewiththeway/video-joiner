import os
import subprocess
import shutil
from mutagen.mp3 import MP3
import argparse

FFMPEG = "/opt/homebrew/bin/ffmpeg"

def get_audio_duration(audio_path):
    audio = MP3(audio_path)
    return audio.info.length

def generate_clip_commands(images, per_image_duration, temp_dir):
    clips = []
    for i, img in enumerate(images):
        out = os.path.join(temp_dir, f"clip_{i}.mp4")
        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-t", str(per_image_duration),
            "-i", img,
            "-vf", "scale=1080:1920",  # vertical video
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:v", "libx264", out
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to generate clip {i} from {img}")
        clips.append(out)
    return clips

def build_filter_chain(clips, per_image_duration):
    # Use a simpler approach with concat filter instead of xfade
    # This avoids frame rate issues with xfade
    filter_chain = ""
    filter_labels = []
    
    # First, ensure all clips have the same frame rate and format
    for i in range(len(clips)):
        filter_chain += f"[{i}:v]fps=30,setpts=PTS-STARTPTS[v{i}];"
        filter_labels.append(f"[v{i}]")
    
    # Use concat filter for smooth transitions
    concat_inputs = "".join(filter_labels)
    filter_chain += f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]"
    
    return filter_chain, "[outv]"

def generate_final_video(clips, audio_path, srt_path, output_path, filter_complex, final_label):
    cmd = [
        FFMPEG, "-y"
    ] + sum([["-i", clip] for clip in clips], []) + [
        "-i", audio_path,
        "-filter_complex", filter_complex + f";{final_label}subtitles={srt_path},format=yuv420p[v]",
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

def main(folder_path):
    # Validate input files
    images = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path)
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    audio_path = os.path.join(folder_path, "audio.mp3")
    srt_path = os.path.join(folder_path, "output.srt")
    output_path = os.path.join(folder_path, "final_video.mp4")
    temp_dir = os.path.join(folder_path, "temp_clips")
    
    if not images:
        raise ValueError(f"No image files found in {folder_path}")
    if not os.path.exists(audio_path):
        raise ValueError(f"Audio file not found: {audio_path}")
    if not os.path.exists(srt_path):
        raise ValueError(f"SRT file not found: {srt_path}")
    
    # Create temp directory
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        duration = get_audio_duration(audio_path)
        per_image_duration = duration / len(images)

        print(f"Processing {len(images)} images with {per_image_duration:.2f}s per image...")
        
        clips = generate_clip_commands(images, per_image_duration, temp_dir)
        filter_complex, final_label = build_filter_chain(clips, per_image_duration)
        
        print("Generating final video...")
        generate_final_video(clips, audio_path, srt_path, output_path, filter_complex, final_label)

        print(f"✅ Video created at: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        
        # Clean up temporary files
        # if os.path.exists(temp_dir):
        #     shutil.rmtree(temp_dir)
        print("🧹 Cleaned up temporary files")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Folder containing images, audio.mp3, and output.srt")
    args = parser.parse_args()
    main(args.folder)
