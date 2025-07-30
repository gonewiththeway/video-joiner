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

def format_time_readable(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02}:{s:02}"

def parse_time_readable(time_str):
    """Parse MM:SS format back to seconds"""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0

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

def parse_edited_subtitles(txt_path):
    """Parse an edited text file back into chunks for ASS generation"""
    chunks = []
    current_chunk = []
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for phrase header: "Phrase X: [MM:SS - MM:SS]"
        if line.startswith("Phrase ") and ":" in line and "[" in line and "]" in line:
            # Extract timing
            timing_match = re.search(r'\[(\d{2}:\d{2}) - (\d{2}:\d{2})\]', line)
            if timing_match:
                phrase_start = parse_time_readable(timing_match.group(1))
                phrase_end = parse_time_readable(timing_match.group(2))
                
                # Find the text line (next line should be "Text: ...")
                i += 1
                if i < len(lines) and lines[i].strip().startswith("Text:"):
                    text_line = lines[i].strip()
                    text = text_line.replace("Text:", "").strip()
                    
                    # Split text into words and create word objects
                    words = text.split()
                    word_duration = (phrase_end - phrase_start) / len(words)
                    
                    word_objects = []
                    for j, word in enumerate(words):
                        word_start = phrase_start + (j * word_duration)
                        word_end = phrase_start + ((j + 1) * word_duration)
                        word_objects.append({
                            'word': word,
                            'start': word_start,
                            'end': word_end
                        })
                    
                    chunks.append(word_objects)
        
        i += 1
    
    return chunks

def regenerate_ass_from_edited_txt(txt_path, ass_path):
    """Regenerate ASS file from edited text file"""
    print(f"📝 Parsing edited subtitles from: {txt_path}")
    chunks = parse_edited_subtitles(txt_path)
    
    if not chunks:
        raise ValueError("No valid subtitle data found in text file. Please check the format.")
    
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
    
    print(f"✅ Regenerated ASS file: {ass_path}")

def generate_readable_subtitles(chunks, txt_path):
    """Generate a human-readable text file with timing information"""
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("SUBTITLE TRANSCRIPT WITH TIMING\n")
        f.write("=" * 50 + "\n\n")
        f.write("INSTRUCTIONS FOR EDITING:\n")
        f.write("- Edit the 'Text:' lines to change subtitle content\n")
        f.write("- Keep the timing format: [MM:SS - MM:SS]\n")
        f.write("- After editing, run: python generate_subs.py --regenerate-from-txt\n")
        f.write("=" * 50 + "\n\n")
        
        for chunk_idx, chunk in enumerate(chunks):
            phrase_words = [w['word'] for w in chunk]
            phrase_text = ' '.join(phrase_words)
            
            # Get timing for the phrase
            start_time = format_time_readable(chunk[0]['start'])
            end_time = format_time_readable(chunk[-1]['end'])
            
            f.write(f"Phrase {chunk_idx + 1}: [{start_time} - {end_time}]\n")
            f.write(f"Text: {phrase_text}\n")
            f.write("-" * 30 + "\n")
            
            # Show individual words with timing
            for i, word in enumerate(chunk):
                word_start = format_time_readable(word['start'])
                word_end = format_time_readable(word['end'])
                f.write(f"  Word {i+1}: [{word_start}-{word_end}] {word['word']}\n")
            f.write("\n")

def generate_ass_subtitles(audio_path, ass_path, model_path=None, max_words_per_chunk=4, generate_txt=True):
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

    # Generate readable text file if requested
    if generate_txt:
        txt_path = ass_path.replace('.ass', '.txt')
        generate_readable_subtitles(chunks, txt_path)
        print(f"📝 Readable subtitles saved to: {txt_path}")

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
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate subtitles from audio file")
    parser.add_argument("audio_path", nargs='?', help="Path to the audio file (WAV format)")
    parser.add_argument("output_path", nargs='?', help="Path for the output ASS subtitle file")
    parser.add_argument("--model-path", help="Path to Vosk model directory")
    parser.add_argument("--max-words", type=int, default=4, help="Maximum words per chunk")
    parser.add_argument("--no-txt", action="store_true", help="Don't generate readable text file")
    parser.add_argument("--regenerate-from-txt", help="Regenerate ASS file from edited text file")
    
    args = parser.parse_args()
    
    if args.regenerate_from_txt:
        # Regenerate ASS from edited text file
        txt_path = args.regenerate_from_txt
        ass_path = txt_path.replace('.txt', '.ass')
        regenerate_ass_from_edited_txt(txt_path, ass_path)
    elif args.audio_path and args.output_path:
        # Normal subtitle generation
        generate_ass_subtitles(
            args.audio_path, 
            args.output_path, 
            args.model_path, 
            args.max_words,
            generate_txt=not args.no_txt
        )
    else:
        parser.print_help() 