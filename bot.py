import requests
from pyrogram import Client, filters
import logging
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


def discover_latest_movies(days, include_upcoming=False):
    """Discover Hindi-language titles released in India within the last `days` days."""
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days)
    endpoint = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": "hi",
        "region": "IN",
        "sort_by": "primary_release_date.desc",
        "primary_release_date.gte": start_date.isoformat(),
        "primary_release_date.lte": today.isoformat(),
        "page": 1
    }
    if include_upcoming:
        params["include_adult"] = False
        params["include_video"] = True

    results = []
    try:
        while True:
            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for movie in data.get("results", []):
                results.append({
                    "title": movie.get("title"),
                    "date": movie.get("release_date"),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None
                })
            if data.get("page") >= data.get("total_pages") or len(results) >= 50:
                break
            params["page"] += 1
    except Exception as e:
        logger.error(f"TMDb discover error: {e}")
    return results


def tmdb_trending(media_type="all", time_window="day"):
    """Get trending items in India from TMDb."""
    endpoint = f"https://api.themoviedb.org/3/trending/{media_type}/{time_window}"
    params = {"api_key": TMDB_API_KEY, "region": "IN"}
    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        trends = []
        for item in data.get("results", [])[:20]:
            trends.append({
                "title": item.get("title") or item.get("name"),
                "media_type": item.get("media_type"),
                "date": item.get("release_date") or item.get("first_air_date")
            })
        return trends
    except Exception as e:
        logger.error(f"TMDb trending error: {e}")
        return []


@app.on_message(filters.command("latest"))
async def latest_handler(client, message):
    """/latest <days> [upcoming]
    List Hindi titles released in India in the last N days (include upcoming if specified)."""
    cmd = message.command
    if len(cmd) < 2 or not cmd[1].isdigit():
        return await message.reply_text("Usage: `/latest <days> [upcoming]` e.g. `/latest 7` or `/latest 1 upcoming`")
    days = int(cmd[1])
    include_up = len(cmd) > 2 and cmd[2].lower() == "upcoming"
    movies = discover_latest_movies(days, include_upcoming=include_up)
    if not movies:
        return await message.reply_text(f"No Hindi titles found in the last {days} day(s).")

    text = f"Hindi releases in the last {days} day(s){' (including upcoming)' if include_up else ''}:\n"
    for idx, m in enumerate(movies, 1):
        text += f"{idx}. {m['title']} ({m['date']})\n"
        if idx >= 20:
            break
    await message.reply_text(text)


@app.on_message(filters.command("trending"))
async def trending_handler(client, message):
    """/trending [media] [time]
    Show trending Indian movies/TV/all.
    media: movie, tv, all (default all)
    time: day, week (default day)"""
    cmd = message.command
    media = cmd[1] if len(cmd) > 1 and cmd[1] in {"movie", "tv", "all"} else "all"
    window = cmd[2] if len(cmd) > 2 and cmd[2] in {"day", "week"} else "day"
    trends = tmdb_trending(media_type=media, time_window=window)
    if not trends:
        return await message.reply_text("Couldn't fetch trending data.")

    text = f"Trending {media.capitalize()} ({window}):\n"
    for idx, t in enumerate(trends, 1):
        text += f"{idx}. [{t['media_type']}] {t['title']} ({t['date']})\n"
    await message.reply_text(text)


@app.on_message(filters.command("movielink"))
async def movielink_handler(client, message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/movielink <movie name> <link>`")
    movie_name = " ".join(message.command[1:-1])
    link = message.command[-1]
    # Keep original search after 2020
    # ... existing fetch_movies_after_year logic could be here if desired
    await message.reply_text("Use /latest or /trending for discovery commands.")


if __name__ == "__main__":
    app.run()
