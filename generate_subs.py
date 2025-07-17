from vosk import Model, KaldiRecognizer
import wave
import json

# Load the Hindi model
model = Model("vosk-model-small-hi-0.22")

# Open your converted audio file
wf = wave.open("output.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())
rec.SetWords(True)

results = []

# Process audio in chunks
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        results.append(json.loads(rec.Result()))
results.append(json.loads(rec.FinalResult()))


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# Save subtitles
with open("subtitles.srt", "w", encoding="utf-8") as f:
    index = 1
    for r in results:
        if 'result' not in r:
            continue
        for word in r['result']:
            start = word['start']
            end = word['end']
            text = word['word']
            f.write(f"{index}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")
            index += 1
