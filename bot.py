import re
import requests
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
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

app = Client(
    "movie_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Per-user state
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

# -------------------- /start --------------------

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Latest", callback_data="latest_menu"),
         InlineKeyboardButton("🎬 Upcoming", callback_data="upcoming_menu")],
        [InlineKeyboardButton("📈 Trending", callback_data="trending_now")],
        [InlineKeyboardButton("🎞️ Movie Link Uploader", callback_data="movie_link_start")]
    ])
    await message.reply(
        "👋 <b>Welcome to MovieBot</b> 🎥\n"
        "Get the latest and trending Hindi movie details, or upload links with style!\n"
        "Choose an option below to begin:",
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )

# -------------------- Callbacks --------------------

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    data = query.data
    uid = query.from_user.id

    # Latest
    if data == "latest_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="latest_1"),
             InlineKeyboardButton("2 Days", callback_data="latest_2")],
            [InlineKeyboardButton("10 Days", callback_data="latest_10")]
        ])
        return await query.message.edit_text(
            "Choose how many days of latest Hindi releases to view:",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )
    if data.startswith("latest_"):
        days = int(data.split("_")[1])
        today = datetime.utcnow().date()
        movies = discover_movies_window(today - timedelta(days=days-1), today)
        text = "🔥 Releases last {} days:\n\n".format(days)
        text += "\n".join(f"{i}. 🎬 {m['title']} ({m['date']})" for i,m in enumerate(movies,1)) or "No Hindi titles found."
        return await query.message.edit_text(text, parse_mode=ParseMode.HTML)

    # Upcoming
    if data == "upcoming_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="upcoming_1"),
             InlineKeyboardButton("2 Days", callback_data="upcoming_2")],
            [InlineKeyboardButton("10 Days", callback_data="upcoming_10")]
        ])
        return await query.message.edit_text(
            "Choose how many days of upcoming Hindi releases to view:",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )
    if data.startswith("upcoming_"):
        days = int(data.split("_")[1])
        today = datetime.utcnow().date()
        movies = discover_movies_window(today, today+timedelta(days=days))
        text = "🎬 Upcoming next {} days:\n\n".format(days)
        text += "\n".join(f"{i}. 🎥 {m['title']} ({m['date']})" for i,m in enumerate(movies,1)) or "No upcoming Hindi titles found."
        return await query.message.edit_text(text, parse_mode=ParseMode.HTML)

    # Trending
    if data == "trending_now":
        trends = tmdb_trending_india()
        text = "📈 Trending this week:\n\n"
        text += "\n".join(f"{i}. 📺 {t['title']} ({t['date']})" for i,t in enumerate(trends,1)) or "No trending content found."
        return await query.message.edit_text(text, parse_mode=ParseMode.HTML)

    # Movie Link
    if data == "movie_link_start":
        link_flow_state[uid] = {}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("@Team_HDT", callback_data="set_team_team_hdt"),
             InlineKeyboardButton("@ORGSupport", callback_data="set_team_orgsupport")]
        ])
        return await query.message.edit_text(
            "Choose your team handle:", reply_markup=kb, parse_mode=ParseMode.HTML
        )
    if data.startswith("set_team_"):
        handle = "@" + data.split("_")[-1]
        link_flow_state[uid]["team"] = handle
        movie_options.pop(uid, None)
        return await query.message.edit_text(
            "Great! Now send me your movie name and link in one message.",
            parse_mode=ParseMode.HTML
        )

# -------------------- Movie Input --------------------
@app.on_message(filters.text & ~filters.regex(r"^/") & ~filters.reply)
async def handle_movie_input(client, message: Message):
    uid = message.from_user.id
    if uid not in link_flow_state or uid in movie_options:
        return
    text = message.text.strip()
    match = re.search(r"https?://\S+", text)
    if not match:
        return await message.reply("<b>Please send both movie name and link.</b>", parse_mode=ParseMode.HTML)

    link = match.group(0)
    name = re.sub(r"https?://\S+", "", text).strip()
    resp = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={name}", timeout=10
    ).json()
    opts = [m for m in resp.get("results", []) if m.get("poster_path") and m.get("release_date", "").startswith(("2021","2022","2023","2024","2025"))]
    if not opts:
        return await message.reply("<b>No matches found.</b>", parse_mode=ParseMode.HTML)

    movie_options[uid] = {"opts": opts[:5], "link": link, "team": link_flow_state[uid]["team"]}
    reply = "<b>Select a movie by number:</b>\n\n"
    reply += "\n".join(f"{i}. 🎬 {m['title']} ({m['release_date']})" for i,m in enumerate(movie_options[uid]["opts"],1))
    await message.reply(reply, parse_mode=ParseMode.HTML)

# -------------------- Number Reply --------------------
@app.on_message(filters.regex(r"^\d+$"))
async def handle_number_reply(client, message: Message):
    uid = message.from_user.id
    if uid not in movie_options:
        return
    choice = int(message.text)
    data = movie_options[uid]
    if choice < 1 or choice > len(data["opts"]):
        return await message.reply("<b>Invalid choice.</b>", parse_mode=ParseMode.HTML)

    m = data["opts"][choice-1]
    link = data["link"]
    team = data["team"]
    img = m.get("poster_path")
    img_url = f"https://image.tmdb.org/t/p/w500{img}" if img else None
    caption = (
        f"<b>🎬 {m['title']}</b>\n"
        f"📅 Released: <b>{m['release_date']}</b>\n\n"
        f"🔗 <a href=\"{link}\">480p</a> | <a href=\"{link}\">720p</a> | <a href=\"{link}\">1080p</a>\n\n"
        f"🔔 Stay Updated: {team}"
    )
    await client.send_photo(
        message.chat.id, img_url,
        caption=caption,
        parse_mode=ParseMode.HTML
    )
    movie_options.pop(uid, None)
    link_flow_state.pop(uid, None)

if __name__ == "__main__":
    app.run()
