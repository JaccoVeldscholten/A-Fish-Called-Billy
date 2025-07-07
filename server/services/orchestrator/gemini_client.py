import requests
import json
import logging
from typing import Optional

# Import the configuration from our own config.py file
from .config import GOOGLE_API_KEY, GEMINI_API_URL, GEMINI_REQUEST_TIMEOUT, GEMINI_PERSONA_INSTRUCTIONS

log = logging.getLogger(__name__)

def get_gemini_response(user_prompt: str) -> Optional[str]:
    """
    Sends a prompt to the Gemini API and returns the text response.
    This function is robust and includes extensive error handling.

    Args:
        user_prompt: The user's prompt (the transcribed text).

    Returns:
        The text of the Gemini response, or None if an error occurs.
    """
    if not GEMINI_API_URL:
        log.error("Gemini API URL is not configured. Is GOOGLE_API_KEY missing?")
        return None

    log.info("Sending request to the Google Gemini API...")

    full_prompt = f"{GEMINI_PERSONA_INSTRUCTIONS}\n\nUser: {user_prompt}"

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # Safety settings to prevent content from being blocked
        "safetySettings": [
           {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
           {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
           {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
           {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }

    try:
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=data,
            timeout=GEMINI_REQUEST_TIMEOUT
        )
        response.raise_for_status()  # Stops on HTTP errors (4xx or 5xx)

        response_data = response.json()

        # Robust way to extract the text
        candidates = response_data.get('candidates')
        if not candidates:
            log.error(f"Gemini response contains no 'candidates'. Response: {response_data}")
            return None

        content = candidates[0].get('content')
        if not content or not content.get('parts'):
            log.error(f"Gemini candidate contains no 'content' or 'parts'. Candidate: {candidates[0]}")
            return None

        text_response = content['parts'][0].get('text')
        if text_response is None:
            log.error(f"Text part in Gemini response contains no 'text' field. Part: {content['parts'][0]}")
            return None
        
        log.info("Successfully received response from Gemini.")
        return text_response.strip()

    except requests.exceptions.RequestException as e:
        log.error(f"HTTP request to Gemini API failed: {e}")
        return None
    except json.JSONDecodeError:
        log.error(f"Could not decode JSON from Gemini API. Status: {response.status_code}, Text: {response.text}")
        return None
    except Exception as e:
        log.error(f"An unexpected error occurred with the Gemini API: {e}", exc_info=True)
        return None