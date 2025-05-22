import re
import requests
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    Message, CallbackQuery
)
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Credentials
API_ID = "29754529"
API_HASH = "dd54732e78650479ac4fb0e173fe4759"
BOT_TOKEN = "7624981552:AAGHzGUItHecmxxp2oCrP6j3Wk6vtgxnH2I"
TMDB_API_KEY = "1eacddf9bc17e39d80e6144ab49cad71"

app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

movie_options = {}
link_flow_state = {}

# -------------------- TMDB Functions --------------------

def discover_movies_window(start_date, end_date):
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

def tmdb_trending_india():
    endpoint = "https://api.themoviedb.org/3/trending/all/week"
    params = {"api_key": TMDB_API_KEY}
    items = []
    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        data = resp.json()
        for it in data.get("results", [])[:20]:
            lang = it.get("original_language")
            country = it.get("origin_country", [])
            if lang == "hi" or (isinstance(country, list) and "IN" in country):
                items.append({
                    "title": it.get("title") or it.get("name"),
                    "media_type": it.get("media_type"),
                    "date": it.get("release_date") or it.get("first_air_date"),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{it.get('poster_path')}" if it.get('poster_path') else None
                })
        return items
    except Exception as e:
        logger.error(f"Trending error: {e}")
        return []

# -------------------- Start + Buttons --------------------

@app.on_message(filters.command("start"))
async def start(client, message):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔥 Latest", callback_data="latest_menu"),
            InlineKeyboardButton("🎬 Upcoming", callback_data="upcoming_menu")
        ],
        [
            InlineKeyboardButton("📈 Trending", callback_data="trending_now")
        ],
        [
            InlineKeyboardButton("🎞️ Movie Link Uploader", callback_data="movie_link_start")
        ]
    ])
    await message.reply("""
👋 Welcome to **MovieBot** 🎥

Get the latest and trending **Hindi** movie details, or upload links with style!
Choose an option below to begin:
""", reply_markup=kb)

# -------------------- Callback Handlers --------------------

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data.startswith("latest_menu"):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="latest_1"), InlineKeyboardButton("2 Days", callback_data="latest_2")],
            [InlineKeyboardButton("10 Days", callback_data="latest_10")]
        ])
        await query.message.edit_text("Choose how many days of latest Hindi releases to view:", reply_markup=kb)

    elif data.startswith("latest_"):
        days = int(data.split("_")[1])
        today = datetime.utcnow().date()
        start = today - timedelta(days=days - 1)
        movies = discover_movies_window(start, today)
        if not movies:
            await query.message.edit_text("No Hindi titles found.")
            return
        text = f"🔥 Hindi releases in the last {days} day(s):\n\n"
        for idx, m in enumerate(movies, 1):
            text += f"{idx}. 🎬 {m['title']} ({m['date']})\n"
        await query.message.edit_text(text)

    elif data.startswith("upcoming_menu"):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="upcoming_1"), InlineKeyboardButton("2 Days", callback_data="upcoming_2")],
            [InlineKeyboardButton("10 Days", callback_data="upcoming_10")]
        ])
        await query.message.edit_text("Choose how many days of upcoming Hindi releases to view:", reply_markup=kb)

    elif data.startswith("upcoming_"):
        days = int(data.split("_")[1])
        today = datetime.utcnow().date()
        end = today + timedelta(days=days)
        upcoming = discover_movies_window(today, end)
        if not upcoming:
            await query.message.edit_text("No upcoming Hindi titles found.")
            return
        text = f"🎬 Upcoming Hindi titles in the next {days} day(s):\n\n"
        for idx, m in enumerate(upcoming, 1):
            text += f"{idx}. 🎥 {m['title']} ({m['date']})\n"
        await query.message.edit_text(text)

    elif data == "trending_now":
        trends = tmdb_trending_india()
        if not trends:
            await query.message.edit_text("No trending content found.")
            return
        text = f"📈 Trending Hindi Movies/Shows (This Week):\n\n"
        for idx, t in enumerate(trends, 1):
            text += f"{idx}. 📺 {t['title']} ({t['date']})\n"
        await query.message.edit_text(text)

    elif data == "movie_link_start":
        link_flow_state[user_id] = {}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("@Team_HDT", callback_data="set_team_team_hdt"),
             InlineKeyboardButton("@ORGSupport", callback_data="set_team_orgsupport")]
        ])
        await query.message.edit_text("Choose your team for movie link branding:", reply_markup=kb)

    elif data.startswith("set_team_"):
        team = data.replace("set_team_", "@")
        link_flow_state[user_id]["team"] = team
        await query.message.edit_text("Now send the *movie name* and *any link* in the same message:", parse_mode="markdown")

# -------------------- Handle User Text --------------------

@app.on_message(filters.text & ~filters.command())
async def handle_movie_input(client, message: Message):
    user_id = message.from_user.id
    if user_id not in link_flow_state or "team" not in link_flow_state[user_id]:
        return

    text = message.text.strip()
    link_match = re.search(r"https?://\S+", text)
    if not link_match:
        return await message.reply("Please include a valid link with the movie name.")

    link = link_match.group(0)
    movie_name = re.sub(r"https?://\S+", "", text).strip()

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
        return await message.reply("No recent movie found with that name.")

    movie_options[user_id] = {"options": options, "link": link, "team": link_flow_state[user_id]["team"]}
    text = "Select the movie you meant by replying with its number:\n\n"
    for i, m in enumerate(options, 1):
        text += f"{i}. 🎬 {m['title']} ({m['date']})\n"
    await message.reply(text)

@app.on_message(filters.text & filters.reply)
async def handle_number_reply(client, message: Message):
    user_id = message.from_user.id
    if user_id not in movie_options:
        return
    if not message.text.isdigit():
        return await message.reply("Please reply with a valid number.")

    choice = int(message.text)
    opts, link, team = movie_options[user_id]['options'], movie_options[user_id]['link'], movie_options[user_id]['team']

    if choice < 1 or choice > len(opts):
        return await message.reply("Invalid choice.")

    m = opts[choice - 1]
    caption = f"""
🎬 **{m['title']}**
📅 Released: **{m['date']}**

📺 Watch in: `Hindi` | `English` | `Tamil` | `Telugu`

🔗 Select Quality:
▪️ 480p: [Click Here]({link})
▪️ 720p: [Click Here]({link})
▪️ 1080p: [Click Here]({link})

🔔 Stay Updated with {team}
"""
    await client.send_photo(message.chat.id, m['poster_url'], caption=caption, parse_mode="markdown")
    movie_options.pop(user_id, None)
    link_flow_state.pop(user_id, None)

if __name__ == "__main__":
    app.run()
