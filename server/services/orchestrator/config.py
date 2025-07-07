import os
import logging
from dotenv import load_dotenv



DEBUG_MODE = True

# --- THESE LINES ARE THE KEY ---
# Load the variables from the .env file in the project's root directory.
# The path is determined relative to this config.py file.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'docker', '.env')
load_dotenv(dotenv_path=dotenv_path)
# --- END OF MODIFICATION ---

# Basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- API en Service Configuratie ---

# Get the API key from the environment. This is now automatically populated by load_dotenv().
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    log.error("IMPORTANT: GOOGLE_API_KEY not found. Make sure it's in your .env file.")

# Service URLs for Docker containers
SST_URL = "http://localhost:5001/inference"
TTS_URL = "http://localhost:5003/api/tts"

# Gemini API endpoint configuratie
GEMINI_MODEL_NAME = "gemini-1.5-flash"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# Construct the complete URL, but only if the API key exists.
GEMINI_API_URL = f"{GEMINI_API_BASE_URL}/{GEMINI_MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}" if GOOGLE_API_KEY else None

# Network timeout for the request
GEMINI_REQUEST_TIMEOUT = 20 # in seconden

# --- Persona/Instructions for the AI ---
GEMINI_PERSONA_INSTRUCTIONS = """
You are a helpful, English-speaking assistant.
Answer the user's question briefly, clearly, and concisely.
Don't use markdown or special formatting.
Your answers are meant to be rendered via speech.
You are also a fish.
You are friendly, but also a bit sarcastic and humorous.
You can also be a bit silly, but not too much.
"""


ANALYZER_URL = "http://localhost:5004/analyze"