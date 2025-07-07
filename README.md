# Video Generator Script

This script creates a video by combining images with audio, overlaying text from a transcript, and adding a glitter effect.

## Setup

1. **Virtual Environment**: Already created and activated
2. **Dependencies**: Already installed via `pip install -r requirements.txt`

## Required Files

Before running the script, you need to provide these files:

1. **`images/`** - A folder containing your image files (JPG or PNG format)
2. **`audio.mp3`** - Your audio file in MP3 format
3. **`transcript.txt`** - A text file containing the transcript/text to overlay
4. **`glitter_overlay.mp4`** - A video file with glitter/sparkle effects to overlay

## Usage

1. Activate the virtual environment:

   ```bash
   source env/bin/activate
   ```

2. Run the script:
   ```bash
   python3 video_generator.py
   ```

## Output

The script will generate `final_video.mp4` with:

- Images displayed in sequence
- Audio synchronized with the duration
- Text overlays at the bottom of each image
- Glitter overlay effect
- Crossfade transitions between images

## Customization

You can modify the following settings in the script:

- `images_folder`: Path to your images folder
- `audio_file`: Path to your audio file
- `transcript_file`: Path to your transcript file
- `output_file`: Name of the output video file
- `glitter_file`: Path to your glitter overlay video

## Notes

- The script automatically calculates timing based on audio duration and number of images
- Images are displayed in alphabetical order
- Text is split evenly across all images
- Video output is at 24 FPS
