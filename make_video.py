import os
import subprocess
import shutil
from mutagen.mp3 import MP3
import argparse
import re

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

def srt_time_to_ass_time(srt_time):
    h, m, s_ms = srt_time.split(':')
    s, ms = s_ms.split(',')
    h = str(int(h))
    ms = str(int(round(int(ms) / 10.0))).zfill(2)
    return f"{h}:{m}:{s}.{ms}"

def convert_srt_to_ass(srt_path, ass_path, style="modern"):
    """Convert SRT to ASS format with custom styling for reels"""
    
    # Different style options for reels
    styles = {
        "modern": {
            "font": "Lava Devanagari",
            "size": "23",
            "outline": "1",
            "shadow": "1",
            "margin_v": "40",
            "alignment": "2"  # Center
        },
        "elegant": {
            "font": "Lava Devanagari",
            "size": "23",
            "outline": "2",
            "shadow": "1",
            "margin_v": "100",
            "alignment": "2"  # Center
        },
        "bold": {
            "font": "Lava Devanagari",
            "size": "23",
            "outline": "4",
            "shadow": "3",
            "margin_v": "140",
            "alignment": "2"  # Center
        },
        "minimal": {
            "font": "Lava Devanagari",
            "size": "23",
            "outline": "1",
            "shadow": "0",
            "margin_v": "80",
            "alignment": "2"  # Center
        }
    }
    
    selected_style = styles.get(style, styles["modern"])
    
    # ASS header with custom styling
    ass_header = f"""[Script Info]
Title: Reel Subtitles
ScriptType: v4.00+
WrapStyle: 1
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{selected_style['font']},{selected_style['size']},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{selected_style['outline']},{selected_style['shadow']},{selected_style['alignment']},50,50,{selected_style['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()
    
    # Parse SRT content
    subtitle_blocks = srt_content.strip().split('\n\n')
    ass_events = []
    
    for block in subtitle_blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # Skip subtitle number
            time_line = lines[1]
            text_lines = lines[2:]
            
            # Parse time
            time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', time_line)
            if time_match:
                start_time = srt_time_to_ass_time(time_match.group(1))
                end_time = srt_time_to_ass_time(time_match.group(2))
                
                # Combine text lines
                text = '\\N'.join(text_lines)
                
                # Create ASS event line
                ass_event = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
                ass_events.append(ass_event)
    
    # Write ASS file
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        f.write('\n'.join(ass_events))
    
    return ass_path

def main(folder_path, style="modern"):
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
        raise ValueError(f"SRT file not found: {ass_path}")
    
    # Create temp directory
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        duration = get_audio_duration(audio_path)
        per_image_duration = duration / len(images)

        print(f"Processing {len(images)} images with {per_image_duration:.2f}s per image...")
        
        clips = generate_clip_commands(images, per_image_duration, temp_dir)
        filter_complex, final_label = build_filter_chain(clips, per_image_duration)
        ass_path = convert_srt_to_ass(srt_path, os.path.join(temp_dir, "output.ass"), style)

        print("Generating final video...")
        generate_final_video(clips, audio_path, ass_path, output_path, filter_complex, final_label)

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
    parser.add_argument("folder", help="Folder containing images, audio.mp3, and output.ass")
    parser.add_argument("--style", choices=["modern", "elegant", "bold", "minimal"], 
                       default="modern", help="Subtitle style for reels")
    args = parser.parse_args()
    main(args.folder, args.style)
