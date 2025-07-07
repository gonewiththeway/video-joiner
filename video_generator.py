import os
import moviepy

# SETTINGS
images_folder = "images"
audio_file = "audio.mp3"
transcript_file = "transcript.txt"
output_file = "final_video.mp4"
glitter_file = "glitter_8x.mp4"  # Your downloaded sparkle overlay

# Load audio using moviepy instead of pydub
audio_clip = moviepy.AudioFileClip(audio_file)
audio_duration = audio_clip.duration

# Load images
images = sorted([os.path.join(images_folder, f) for f in os.listdir(images_folder) if f.endswith(('.jpg','.png'))])
num_images = len(images)
sec_per_image = audio_duration / num_images

# Load transcript & split
with open(transcript_file, 'r') as f:
    transcript = f.read()
words = transcript.split()
words_per_image = len(words) // num_images
chunks = [" ".join(words[i*words_per_image : (i+1)*words_per_image]) for i in range(num_images)]

# Build clips
clips = []
for img_path, text in zip(images, chunks):
    img_clip = moviepy.ImageClip(img_path).with_duration(sec_per_image)
    # For now, skip text overlay to get basic functionality working
    # txt_clip = moviepy.TextClip(text=text, font_size=40, color='white').with_duration(sec_per_image)
    # txt_clip = txt_clip.with_position('bottom').with_margin(bottom=30, opacity=0)
    # composite = moviepy.CompositeVideoClip([img_clip, txt_clip])
    clips.append(img_clip)

# Crossfade
final = moviepy.concatenate_videoclips(clips, method="compose", padding=-0.5)

# Add audio
final = final.with_audio(audio_clip)

# Add glitter overlay
glitter = moviepy.VideoFileClip(glitter_file).resized(final.size).with_duration(final.duration)
final = moviepy.CompositeVideoClip([final, glitter])

# Export
final.write_videofile(output_file, fps=24) 