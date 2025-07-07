import wave
import numpy as np
import json
import os
from flask import Flask, request, jsonify, abort
import logging
import re

# --- Constanten & "Enums" voor Redenen ---
class Reason:
    VOLUME_ABOVE_THRESHOLD = "VOLUME_ABOVE_THRESHOLD"
    VOLUME_BELOW_THRESHOLD = "VOLUME_BELOW_THRESHOLD"
    PEAK_DETECTED = "PEAK_DETECTED"
    SPEECH_START = "SPEECH_START"
    SPEECH_END = "SPEECH_END"

# --- ADJUSTED VALUES FOR FINETUNING ---
FRAME_MS = 30
MOUTH_RMS_THRESHOLD = 800
TAIL_PEAK_THRESHOLD = 25000  # INCREASED: Stricter for the tail
HEAD_TURN_PADDING_MS = 150
TAIL_COOLDOWN_MS = 350       # INCREASED: Longer pause between tail flaps

# NEW: "Debounce" to prevent the mouth from opening immediately after closing
MOUTH_DEBOUNCE_MS = 180

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def find_word_by_character_index(text, index):
    """Finds the complete word that contains a specific character index."""
    if index < 0 or index >= len(text):
        return ""
    # Find the start and end of the word
    start = text.rfind(' ', 0, index) + 1
    end = text.find(' ', index)
    if end == -1: end = len(text)
    word = text[start:end]
    return re.sub(r'[^\w\s]', '', word) # Remove punctuation

def perform_analysis(input_wav_path: str, source_text: str) -> dict:
    """Analyzes audio with debouncing for the mouth and stricter tail logic."""
    app.logger.info(f"Starting refined analysis for: {input_wav_path}")
    try:
        with wave.open(input_wav_path, 'rb') as wf:
            framerate, n_frames = wf.getframerate(), wf.getnframes()
            frames = wf.readframes(n_frames)
            audio_data = np.frombuffer(frames, dtype=np.int16)
            duration_ms = (n_frames / float(framerate)) * 1000
    except Exception as e:
        raise IOError(f"Could not read WAV file: {e}")

    chars_per_ms = len(source_text) / (duration_ms + 1)
    events = []
    mouth_is_open = False
    last_tail_flap_time = -TAIL_COOLDOWN_MS
    
    # NEW VARIABLE FOR DEBOUNCING
    last_mouth_close_time = -MOUTH_DEBOUNCE_MS 
    
    samples_per_frame = int(framerate * (FRAME_MS / 1000.0))

    for i in range(0, len(audio_data), samples_per_frame):
        chunk = audio_data[i:i+samples_per_frame]
        if len(chunk) == 0: continue
        timestamp_ms = int((i / framerate) * 1000)
        rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
        peak = np.max(np.abs(chunk))

        estimated_char_index = int(timestamp_ms * chars_per_ms)
        analyzed_word = find_word_by_character_index(source_text, estimated_char_index)
        event = {"timestamp_ms": timestamp_ms, "analyzed_word": analyzed_word}

        # --- ADJUSTED MOUTH LOGIC ---
        # Mouth can only open if it's closed AND the debounce time has passed.
        if rms > MOUTH_RMS_THRESHOLD and not mouth_is_open and (timestamp_ms - last_mouth_close_time > MOUTH_DEBOUNCE_MS):
            event.update({"action": "MOUTH_OPEN", "reason": Reason.VOLUME_ABOVE_THRESHOLD})
            events.append(event)
            mouth_is_open = True
        elif rms <= MOUTH_RMS_THRESHOLD and mouth_is_open:
            event.update({"action": "MOUTH_CLOSE", "reason": Reason.VOLUME_BELOW_THRESHOLD})
            events.append(event)
            mouth_is_open = False
            last_mouth_close_time = timestamp_ms # Update the closing time
        
        # Tail logic (unchanged, but threshold is stricter)
        if peak > TAIL_PEAK_THRESHOLD and (timestamp_ms - last_tail_flap_time > TAIL_COOLDOWN_MS):
            event.update({"action": "TAIL_FLAP", "reason": Reason.PEAK_DETECTED})
            events.append(event)
            last_tail_flap_time = timestamp_ms

    # Head logic (remains the same)
    open_events = [e['timestamp_ms'] for e in events if e['action'] == 'MOUTH_OPEN']
    close_events = [e['timestamp_ms'] for e in events if e['action'] == 'MOUTH_CLOSE']
    if open_events:
        events.append({"timestamp_ms": max(0, min(open_events) - HEAD_TURN_PADDING_MS), "action": "HEAD_TURN_FORWARD", "reason": Reason.SPEECH_START})
    if close_events:
        events.append({"timestamp_ms": int(max(close_events) + HEAD_TURN_PADDING_MS), "action": "HEAD_TURN_BACK", "reason": Reason.SPEECH_END})
    
    return {
        "source_text": source_text,
        "audio_duration_ms": duration_ms,
        "motor_events": sorted(events, key=lambda e: e['timestamp_ms'])
    }

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    # This function remains unchanged
    if not request.json or 'input_path' not in request.json or 'text' not in request.json:
        abort(400, "Bad Request: 'input_path' and/or 'text' missing in JSON body")
    input_filename = os.path.basename(request.json['input_path'])
    source_text = request.json['text']
    full_path = os.path.join('/app/data', input_filename)
    if not os.path.exists(full_path):
        abort(404, f"Not Found: File {full_path} not found")
    try:
        analysis_result = perform_analysis(full_path, source_text)
        return jsonify(analysis_result)
    except Exception as e:
        app.logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        abort(500, "Internal Server Error")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)