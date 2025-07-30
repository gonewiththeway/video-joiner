from vosk import Model, KaldiRecognizer
import wave
import json
import os
import re
import pathlib

def format_time_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)  # centiseconds for ASS
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def is_sentence_end(word):
    # Check if word ends a sentence (has punctuation)
    return word['word'].strip().endswith(('.', '।', '!', '?', ':'))

def create_phrase_chunks(all_words, max_words_per_chunk=4):
    # Group words into phrases/chunks with natural breaks
    chunks = []
    current_chunk = []

    for word in all_words:
        current_chunk.append(word)

        # Break chunk if:
        # 1. We've reached max words
        # 2. Word ends a sentence
        # 3. There's a significant pause (gap > 0.5s)
        should_break = False

        if len(current_chunk) >= max_words_per_chunk:
            should_break = True
        elif is_sentence_end(word):
            should_break = True
        elif len(current_chunk) > 1:
            # Check for pause (gap > 0.5s between words)
            prev_word = current_chunk[-2]
            gap = word['start'] - prev_word['end']
            if gap > 0.5:
                should_break = True

        if should_break:
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def generate_ass_subtitles(audio_path, ass_path, model_path=None, max_words_per_chunk=4):
    # Use absolute path for model if not provided
    if model_path is None:
        model_path = str(pathlib.Path(__file__).parent / "vosk-model-hi-0.22")
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

    # Collect all words with timing
    all_words = []
    for r in results:
        if 'result' not in r:
            continue
        all_words.extend(r['result'])

    # Create phrase chunks
    chunks = create_phrase_chunks(all_words, max_words_per_chunk)

    ass_header = '''[Script Info]
Title: Word Highlight Subtitles
ScriptType: v4.00+
WrapStyle: 1
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Lava Devanagari,35,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,50,50,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

    events = []

    for chunk_idx, chunk in enumerate(chunks):
        phrase_words = [w['word'] for w in chunk]
        for i, word in enumerate(chunk):
            # Build the phrase, highlighting only the current word
            text_parts = []
            for j, w in enumerate(chunk):
                if i == j:
                    # Highlight current word
                    text_parts.append(r'{\b1\c&H00FFFF&\3c&H000000&}' + w['word'] + r'{\r}')
                else:
                    text_parts.append(w['word'])
            text = ' '.join(text_parts)

            # Start time: current word start
            start_time = format_time_ass(word['start'])

            # End time: next word start (or next phrase start if last word)
            if i < len(chunk) - 1:
                # Not the last word - end when next word starts
                end_time = format_time_ass(chunk[i + 1]['start'])
            else:
                # Last word in the phrase
                if chunk_idx < len(chunks) - 1:
                    # Not the last phrase - end when next phrase starts
                    next_phrase_start = chunks[chunk_idx + 1][0]['start']
                    end_time = format_time_ass(next_phrase_start)
                else:
                    # Last phrase - end when the word ends
                    end_time = format_time_ass(word['end'])

            events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")

    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        f.write('\n'.join(events))

    return ass_path

if __name__ == "__main__":
    generate_ass_subtitles("output.wav", "subtitles.ass") 