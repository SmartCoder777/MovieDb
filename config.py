import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if using)
load_dotenv()

# Bot Credentials
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# TMDB API Credentials
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Configuration dictionary
config = {
    "api_id": API_ID,
    "api_hash": API_HASH,
    "bot_token": BOT_TOKEN,
    "tmdb_api_key": TMDB_API_KEY
}
