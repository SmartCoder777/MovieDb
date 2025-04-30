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


def discover_movies_window(start_date, end_date):
    """Discover Hindi titles released in India between start_date and end_date."""
    endpoint = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": "hi",
        "region": "IN",
        "sort_by": "primary_release_date.desc",
        "primary_release_date.gte": start_date.isoformat(),
        "primary_release_date.lte": end_date.isoformat(),
        "page": 1
    }
    results = []
    try:
        while True:
            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for m in data.get("results", []):
                results.append({
                    "title": m.get("title"),
                    "date": m.get("release_date"),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else None
                })
            if data.get("page") >= data.get("total_pages") or len(results) >= 50:
                break
            params["page"] += 1
    except Exception as e:
        logger.error(f"Discover error: {e}")
    return results


def tmdb_trending_india(media_type="all", time_window="day"):  # only Hindi/IN items
    endpoint = f"https://api.themoviedb.org/3/trending/{media_type}/{time_window}"
    params = {"api_key": TMDB_API_KEY}
    items = []
    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for it in data.get("results", [])[:50]:
            lang = it.get("original_language")
            country = it.get("origin_country", [])
            if lang == "hi" or (isinstance(country, list) and "IN" in country):
                items.append({
                    "title": it.get("title") or it.get("name"),
                    "media_type": it.get("media_type"),
                    "date": it.get("release_date") or it.get("first_air_date"),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{it.get('poster_path')}" if it.get('poster_path') else None
                })
        return items[:20]
    except Exception as e:
        logger.error(f"Trending error: {e}")
        return []


@app.on_message(filters.command("latest"))
async def latest_handler(client, message):
    """Usage: /latest <days>
    Show Hindi titles released in the last N days (including today)."""
    cmd = message.command
    if len(cmd) != 2 or not cmd[1].isdigit():
        return await message.reply_text("Usage: `/latest <days>` e.g. `/latest 1` or `/latest 7`")
    days = int(cmd[1])
    today = datetime.utcnow().date()
    start = today - timedelta(days=days-1)
    movies = discover_movies_window(start, today)
    if not movies:
        return await message.reply_text(f"No Hindi titles found in the last {days} day(s).")
    text = f"Hindi releases in the last {days} day(s):\n"
    for idx, m in enumerate(movies, 1):
        text += f"{idx}. {m['title']} ({m['date']})\n"
    await message.reply_text(text)


@app.on_message(filters.command("upcoming"))
async def upcoming_handler(client, message):
    """Usage: /upcoming <days>
    Show Hindi titles upcoming in the next N days (including today)."""
    cmd = message.command
    if len(cmd) != 2 or not cmd[1].isdigit():
        return await message.reply_text("Usage: `/upcoming <days>` e.g. `/upcoming 10`")
    days = int(cmd[1])
    today = datetime.utcnow().date()
    end = today + timedelta(days=days)
    upcoming = discover_movies_window(today, end)
    if not upcoming:
        return await message.reply_text(f"No upcoming Hindi titles in the next {days} day(s).")
    text = f"Upcoming Hindi titles in the next {days} day(s):\n"
    for idx, m in enumerate(upcoming, 1):
        text += f"{idx}. {m['title']} ({m['date']})\n"
    await message.reply_text(text)


@app.on_message(filters.command("trending"))
async def trending_handler(client, message):
    """Usage: /trending [media] [time]
    Show trending Indian content: movies/TV/all (default all), day/week (default day)."""
    cmd = message.command
    media = cmd[1] if len(cmd) > 1 and cmd[1] in {"movie", "tv", "all"} else "all"
    window = cmd[2] if len(cmd) > 2 and cmd[2] in {"day", "week"} else "day"
    trends = tmdb_trending_india(media_type=media, time_window=window)
    if not trends:
        return await message.reply_text("No trending Indian content found.")
    text = f"Trending Indian {media.capitalize()} ({window}):\n"
    for idx, t in enumerate(trends, 1):
        text += f"{idx}. [{t['media_type']}] {t['title']} ({t['date']})\n"
    await message.reply_text(text)


@app.on_message(filters.command("movielink"))
async def movielink_handler(client, message):
    """Usage: /movielink <movie name> <link>
    Search TMDb for a movie (2021+), list options, then pick via reply."""
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/movielink <movie name> <link>`")
    movie_name = " ".join(message.command[1:-1])
    link = message.command[-1]
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    resp = requests.get(url, timeout=10).json()
    options = []
    for m in resp.get("results", []):
        date = m.get("release_date", "")
        if date and int(date.split("-")[0]) >= 2021 and m.get("poster_path"):
            options.append({
                "title": m.get("title"),
                "date": date,
                "poster_url": f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
            })
    if not options:
        return await message.reply_text("No movies found released after 2020.")
    movie_options[message.chat.id] = {"options": options, "link": link}
    text = "Select a movie by number:\n"
    for i, m in enumerate(options, 1):
        text += f"{i}. {m['title']} ({m['date']})\n"
    await message.reply_text(text)


@app.on_message(filters.text & ~filters.regex(r'^/'))
async def handle_selection(client, message):
    data = movie_options.get(message.chat.id)
    if not data or not message.text.isdigit():
        return
    choice = int(message.text)
    opts, link = data['options'], data['link']
    if choice < 1 or choice > len(opts):
        return await message.reply_text("Invalid choice. Reply with a valid number.")
    m = opts[choice-1]
    poster_url = m.get('poster_url')
    if poster_url:
        caption = (
            f"**{m['title']}** **Latest Movie** **{m['date']}**\n\n"
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
        await client.send_photo(message.chat.id, poster_url, caption=caption)
    movie_options.pop(message.chat.id, None)


if __name__ == "__main__":
    app.run()
