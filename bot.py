import requests
from pyrogram import Client, filters
import logging
import time
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Credentials
API_ID = "29754529"
API_HASH = "dd54732e78650479ac4fb0e173fe4759"
BOT_TOKEN = "7814806767:AAEbx6EcJb_PHyGJdjqixZCks_dSJm6WSJY"

# TMDB API Credentials
TMDB_API_KEY = "1eacddf9bc17e39d80e6144ab49cad71"

app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory storage for user movie options
movie_options = {}


def fetch_movies_after_year(movie_name, min_year=2021):
    """Fetch movies from TMDB released in or after min_year."""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    retries = 3
    backoff_time = 2
    results = []

    with requests.Session() as session:
        for attempt in range(retries):
            try:
                response = session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                for movie in data.get("results", []):
                    date = movie.get("release_date", "")
                    if not date:
                        continue
                    year = int(date.split("-")[0])
                    if year >= min_year:
                        poster = movie.get("poster_path")
                        if poster:
                            results.append({
                                "title": movie.get("title"),
                                "year": str(year),
                                "poster_url": f"https://image.tmdb.org/t/p/w500{poster}"
                            })
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching: {e} (Attempt {attempt+1}/{retries})")
                time.sleep(backoff_time)
                backoff_time *= 2
    return results


def fetch_movies_last_days(days):
    """Fetch movies released within the last `days` days using TMDB Discover API."""
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days)
    url = (
        f"https://api.themoviedb.org/3/discover/movie?"
        f"api_key={TMDB_API_KEY}&"
        f"primary_release_date.gte={start_date}&"
        f"primary_release_date.lte={today}&"
        f"sort_by=primary_release_date.desc"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching latest movies: {e}")
        return []


@app.on_message(filters.command("movielink"))
async def list_movie_options(client, message):
    """List all movies released after 2020 matching the query."""
    if len(message.command) < 3:
        await message.reply_text("Usage: `/movielink <movie name> <link>`")
        return

    movie_name = " ".join(message.command[1:-1])
    link = message.command[-1]
    options = fetch_movies_after_year(movie_name)

    if not options:
        await message.reply_text("No movies found released after 2020.")
        return

    movie_options[message.chat.id] = {"options": options, "link": link}

    text = "Found the following movies (reply with the number to select):\n"
    for idx, m in enumerate(options, start=1):
        text += f"{idx}. {m['title']} ({m['year']})\n"

    await message.reply_text(text)


@app.on_message(filters.command("latest"))
async def latest_movies(client, message):
    """List movies released within the last N days."""
    if len(message.command) != 2 or not message.command[1].isdigit():
        await message.reply_text("Usage: `/latest <days>` (e.g. `/latest 7`) to list movies from the last <days> days.")
        return

    days = int(message.command[1])
    results = fetch_movies_last_days(days)
    if not results:
        await message.reply_text(f"No movies found in the last {days} day(s).")
        return

    text = f"Movies released in the last {days} day(s):\n"
    for idx, movie in enumerate(results, start=1):
        # show title and release date
        date = movie.get("release_date", "Unknown")
        text += f"{idx}. {movie.get('title')} ({date})\n"
        if idx >= 20:
            break  # cap to first 20 results

    await message.reply_text(text)


# Selection handler (exclude commands)
@app.on_message(filters.text & ~filters.regex(r'^/'))
async def handle_selection(client, message):
    """Handles numeric selection to send the chosen movie poster."""
    data = movie_options.get(message.chat.id)
    if not data:
        return

    text = message.text.strip()
    if not text.isdigit():
        return

    choice = int(text)
    options = data["options"]
    link = data["link"]

    if choice < 1 or choice > len(options):
        await message.reply_text("Invalid choice. Please reply with a valid number.")
        return

    movie = options[choice-1]
    caption = (
        f"**{movie['title']}** **Latest Movie** **{movie['year']}**\n\n"
        f"LOGIN & WATCH FULL VIDEOS\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📥 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐋𝐢𝐧𝐤𝐬/👀𝐖𝐚𝐭𝐜𝐡 𝐎𝐧𝐥𝐢𝐧𝐞\n\n"
        f"HINDI ENGLISH TAMIL TELUGU\n\n"
        f"480p\n\n{link}\n\n"
        f"720p\n\n{link}\n\n"
        f"1080p\n\n{link}\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"Join @ORGPrime"
    )
    await client.send_photo(message.chat.id, movie["poster_url"], caption=caption)
    movie_options.pop(message.chat.id, None)


if __name__ == "__main__":
    app.run()
