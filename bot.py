import requests
from pyrogram import Client, filters
import logging
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

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
    retries, backoff_time, results = 3, 2, []
    with requests.Session() as session:
        for attempt in range(retries):
            try:
                data = session.get(url, timeout=10).json()
                for movie in data.get("results", []):
                    date = movie.get("release_date", "")
                    if not date:
                        continue
                    year = int(date.split("-")[0])
                    if year >= min_year and movie.get("poster_path"):
                        results.append({
                            "title": movie["title"],
                            "year": str(year),
                            "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
                        })
                break
            except Exception as e:
                logger.error(f"TMDB error: {e}")
                time.sleep(backoff_time); backoff_time *= 2
    return results


def fetch_latest_from_gadgets360(days):
    """Scrape gadgets360 for new Hindi movies and filter by published within `days`."""
    url = "https://www.gadgets360.com/entertainment/new-hindi-movies"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        items = []
        cutoff = datetime.utcnow() - timedelta(days=days)
        # Each movie entry is in <li class="latestNewsList">
        for li in soup.select("ul.latestNewsList li"):  
            a = li.find("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            # Extract date from sibling <span class="time"> if available
            time_span = li.find("span", class_="time")
            pub_date = None
            if time_span:
                try:
                    # e.g. 'Apr 30, 2025'
                    pub_date = datetime.strptime(time_span.get_text(strip=True), "%b %d, %Y")
                except:
                    pub_date = None
            # include if within days or if no date
            if not pub_date or pub_date >= cutoff:
                items.append({"title": title, "date": pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown"})
        return items
    except Exception as e:
        logger.error(f"Gadgets360 scrape error: {e}")
        return []

@app.on_message(filters.command("movielink"))
async def list_movie_options(client, message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/movielink <movie name> <link>`")
    movie_name = " ".join(message.command[1:-1])
    link = message.command[-1]
    options = fetch_movies_after_year(movie_name)
    if not options:
        return await message.reply_text("No movies found released after 2020.")
    movie_options[message.chat.id] = {"options": options, "link": link}
    text = "Found movies after 2020:\n"
    for i, m in enumerate(options, 1): text += f"{i}. {m['title']} ({m['year']})\n"
    await message.reply_text(text)

@app.on_message(filters.command("latest"))
async def latest_movies(client, message):
    if len(message.command) != 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: `/latest <days>` to list new Hindi movies from gadgets360.")
    days = int(message.command[1])
    items = fetch_latest_from_gadgets360(days)
    if not items:
        return await message.reply_text(f"No new Hindi movies found in the last {days} day(s).")
    text = f"New Hindi movies in the last {days} day(s):\n"
    for idx, it in enumerate(items, 1):
        text += f"{idx}. {it['title']} ({it['date']})\n"
        if idx >= 20: break
    await message.reply_text(text)

@app.on_message(filters.text & ~filters.regex(r'^/'))
async def handle_selection(client, message):
    data = movie_options.get(message.chat.id)
    if not data or not message.text.isdigit():
        return
    choice = int(message.text)
    opts, link = data['options'], data['link']
    if choice < 1 or choice > len(opts):
        return await message.reply_text("Invalid choice.")
    m = opts[choice-1]
    caption = (
        f"**{m['title']}** **Latest Movie** **{m['year']}**\n\n"
        f"LOGIN & WATCH FULL VIDEOS\n━━━━━━━━━━━━━━━━━━━\n"
        f"📥 Download Links / 👀 Watch Online\n\n480p {link}\n720p {link}\n1080p {link}\n\nJoin @ORGPrime"
    )
    await client.send_photo(message.chat.id, m['poster_url'], caption=caption)
    movie_options.pop(message.chat.id, None)

if __name__ == "__main__":
    app.run()
