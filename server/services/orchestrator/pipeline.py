import sys
import os
import requests
import logging
import json

from orchestrator.config import SST_URL, TTS_URL, ANALYZER_URL
from orchestrator.gemini_client import get_gemini_response

log = logging.getLogger(__name__)

def run_pipeline(input_wav_path: str):
    """
    Executes the complete pipeline with the correct payload for the analyzer.
    """
    # --- STEP 1 & 2 (unchanged) ---
    log.info(f"Step 1: Transcribing {input_wav_path}...")
    try:
        with open(input_wav_path, 'rb') as f:
            files = {'file': (os.path.basename(input_wav_path), f)}
            params = {'language': 'nl'}
            response = requests.post(SST_URL, files=files, params=params)
            response.raise_for_status()
        transcribed_text = response.json().get('text', '').strip()
        if not transcribed_text:
            log.error("SST service returned empty text.")
            return
        log.info(f"Transcribed text: '{transcribed_text}'")
    except Exception as e:
        log.error(f"Error in SST service: {e}", exc_info=True)
        return

    log.info("Step 2: Generating response with Gemini...")
    gemini_response_text = get_gemini_response(transcribed_text)
    if not gemini_response_text:
        log.error("No response received from Gemini.")
        return
    log.info(f"Response from Gemini: '{gemini_response_text}'")

    # --- STEP 3 (unchanged) ---
    log.info("Step 3: Generating audio with Coqui TTS...")
    try:
        params = {'text': gemini_response_text, 'speaker_id': 'p225'}
        response = requests.get(TTS_URL, params=params)
        response.raise_for_status()
        output_wav_path = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'output', 'response.wav')
        os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
        with open(output_wav_path, 'wb') as f:
            f.write(response.content)
        log.info(f"Step 3 completed! Audio saved in: {output_wav_path}")
    except Exception as e:
        log.error(f"Error in TTS service: {e}", exc_info=True)
        return

    # --- STEP 4: AUDIO ANALYSIS (THE CORRECT WAY) ---
    log.info("Step 4: Analyzing audio for motor instructions...")
    try:
        # THE FIX: We send both the path AND the text that represents the audio.
        payload = {
            'input_path': 'response.wav',
            'text': gemini_response_text
        }
        
        response = requests.post(ANALYZER_URL, json=payload)
        response.raise_for_status()

        instructions_data = response.json()
        
        output_json_path = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'output', 'instructions.json')
        with open(output_json_path, 'w') as f:
            json.dump(instructions_data, f, indent=2)

        log.info(f"Analysis successful. 'instructions.json' has been created.")
        log.info(f"🎉🎉🎉 COMPLETE PIPELINE FINISHED! 🎉🎉🎉")

    except requests.exceptions.HTTPError as e:
        log.error(f"Error in analyzer service: Status {e.response.status_code}, Details: {e.response.text}")
    except Exception as e:
        log.error(f"Unexpected error during audio analysis: {e}", exc_info=True)
        return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m orchestrator.pipeline <path_to_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    run_pipeline(input_file)