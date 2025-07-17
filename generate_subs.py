from vosk import Model, KaldiRecognizer
import wave
import json
import os

def format_time_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)  # centiseconds for ASS
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def generate_ass_subtitles(audio_path, ass_path, model_path="vosk-model-small-hi-0.22"):
    # Load the model
    model = Model(model_path)
    wf = wave.open(audio_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()))
    results.append(json.loads(rec.FinalResult()))

    # ASS header with two styles: normal and highlight
    ass_header = '''[Script Info]
Title: Word Highlight Subtitles
ScriptType: v4.00+
WrapStyle: 1
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Lava Devanagari,40,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,50,50,40,1
Style: Highlight,Lava Devanagari,40,&H0000FFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,2,50,50,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

    events = []
    index = 1
    for r in results:
        if 'result' not in r:
            continue
        words = r['result']
        # Option 1: Only show the current word (most common for reels)
        for word in words:
            start = word['start']
            end = word['end']
            text = word['word']
            start_ass = format_time_ass(start)
            end_ass = format_time_ass(end)
            # Highlight style for the word
            events.append(f"Dialogue: 0,{start_ass},{end_ass},Highlight,,0,0,0,,{text}")
            index += 1
        # Option 2: If you want to show the whole line and highlight the current word, you can build the line and use ASS override tags, but for now, we use Option 1.

    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        f.write('\n'.join(events))

    return ass_path

# If run as a script, generate subtitles for output.wav -> subtitles.ass
if __name__ == "__main__":
    generate_ass_subtitles("output.wav", "subtitles.ass")
