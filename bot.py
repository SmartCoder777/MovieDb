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

# Initialize bot
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


def tmdb_trending_india():
    endpoint = "https://api.themoviedb.org/3/trending/all/week"
    params = {"api_key": TMDB_API_KEY}
    items = []
    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for it in data.get("results", [])[:20]:
            lang = it.get("original_language")
            country = it.get("origin_country", [])
            if lang == "hi" or (isinstance(country, list) and "IN" in country):
                items.append({
                    "title": it.get("title") or it.get("name"),
                    "date": it.get("release_date") or it.get("first_air_date"),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{it.get('poster_path')}" if it.get('poster_path') else None
                })
    except Exception as e:
        logger.error(f"Trending error: {e}")
    return items

# -------------------- /start --------------------
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Latest", callback_data="latest_menu"),
         InlineKeyboardButton("🎬 Upcoming", callback_data="upcoming_menu")],
        [InlineKeyboardButton("📈 Trending", callback_data="trending_now")],
        [InlineKeyboardButton("🎞️ Movie Link Uploader", callback_data="movie_link_start")],
        [InlineKeyboardButton("🎥 Details", callback_data="details_start")]  # Added Details
    ])
    await message.reply(
        "👋 <b>Welcome to MovieBot</b> 🎥\n"
        "Get the latest & trending Hindi movies or share links in style!",
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )

# -------------------- Callback Handlers --------------------
@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    data = query.data
    uid = query.from_user.id

    # Latest releases
    if data == "latest_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="latest_1"),
             InlineKeyboardButton("7 Days", callback_data="latest_7")],
            [InlineKeyboardButton("30 Days", callback_data="latest_30")]
        ])
        await query.message.reply("Choose range for 🔥 Latest releases:", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    if data.startswith("latest_"):
        days = int(data.split("_")[1])
        end = datetime.utcnow().date()
        start = end - timedelta(days=days-1)
        movies = discover_movies_window(start, end)
        if not movies:
            text = "No Hindi releases found."
        else:
            text = f"🔥 Releases in last {days} days:\n" + "\n".join(
                f"{i}. {m['title']} ({m['date']})" for i, m in enumerate(movies, 1)
            )
        await query.message.reply(text, parse_mode=ParseMode.HTML)
        return

    # Upcoming releases
    if data == "upcoming_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("7 Days", callback_data="upcoming_7"),
             InlineKeyboardButton("14 Days", callback_data="upcoming_14")],
            [InlineKeyboardButton("30 Days", callback_data="upcoming_30")]
        ])
        await query.message.reply("Choose range for 🎬 Upcoming:", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    if data.startswith("upcoming_"):
        days = int(data.split("_")[1])
        start = datetime.utcnow().date()
        end = start + timedelta(days=days)
        movies = discover_movies_window(start, end)
        if not movies:
            text = "No upcoming Hindi titles."
        else:
            text = f"🎬 Upcoming in next {days} days:\n" + "\n".join(
                f"{i}. {m['title']} ({m['date']})" for i, m in enumerate(movies, 1)
            )
        await query.message.reply(text, parse_mode=ParseMode.HTML)
        return

    # Trending this week
    if data == "trending_now":
        trends = tmdb_trending_india()
        if not trends:
            text = "No trending content found."
        else:
            text = "📈 Trending this week:\n" + "\n".join(
                f"{i}. {t['title']} ({t['date']})" for i, t in enumerate(trends, 1)
            )
        await query.message.reply(text, parse_mode=ParseMode.HTML)
        return

    # Movie Link flow
    if data == "movie_link_start":
        link_flow_state[uid] = {}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("@Team_HDT", callback_data="team_hdt"),
             InlineKeyboardButton("@ORGSupport", callback_data="team_org")]
        ])
        await query.message.reply("🎞️ Choose your team handle:", reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    if data in ("team_hdt", "team_org"):
        team = "@Team_HDT" if data == "team_hdt" else "@ORGSupport"
        link_flow_state[uid]["team"] = team
        movie_options.pop(uid, None)
        await query.message.reply(
            "✨ Great! Now send <b>Movie Name</b> and <b>Link</b> together:", parse_mode=ParseMode.HTML
        )
        return

    # Details flow start
    if data == "details_start":
        movie_options[uid] = {"mode": "details"}
        await query.message.reply("🔍 Send the <b>Movie Name</b> to get full details.", parse_mode=ParseMode.HTML)
        return

# -------------------- Handle Movie Entry --------------------
@app.on_message(filters.text & ~filters.regex(r"^/") & ~filters.reply)
async def handle_movie_entry(client, message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    # Details mode: movie name received
    if movie_options.get(uid, {}).get("mode") == "details":
        resp = requests.get(
            f"https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_API_KEY, "query": text}, timeout=10
        ).json().get("results", [])
        opts = [o for o in resp if o.get("poster_path")]
        if not opts:
            await message.reply("<b>No movie matches found.</b>", parse_mode=ParseMode.HTML)
            return
        # store choices
        movie_options[uid] = {"mode": "details_choice", "opts": opts[:5]}
        # list top 5
        choices = "\n".join(
            f"{i}. 🎥 <b>{o['title']}</b> ({o.get('release_date','?')})"
            for i, o in enumerate(opts[:5], 1)
        )
        await message.reply(
            f"<b>🔍 Choose a movie:</b>\n{choices}\n\nReply with the number:",
            parse_mode=ParseMode.HTML
        )
        return

    # Uploader flow entry (unchanged original logic)
    if uid in link_flow_state and uid not in movie_options:
        m = re.search(r"https?://\S+", text)
        if not m:
            await message.reply("⚠️ <b>Please include both name and link.</b>", parse_mode=ParseMode.HTML)
            return
        link = m.group(0)
        name = re.sub(r"https?://\S+", "", text).strip()
        resp = requests.get(
            f"https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_API_KEY, "query": name}, timeout=10
        ).json().get("results", [])
        opts = [o for o in resp if o.get("poster_path")]
        if not opts:
            await message.reply("<b>No matches found.</b>", parse_mode=ParseMode.HTML)
            return
        movie_options[uid] = {"opts": opts[:5], "link": link, "team": link_flow_state[uid]["team"]}
        choices = "\n".join(
            f"{i}. 🎥 <b>{o['title']}</b> ({o.get('release_date','?')})"
            for i, o in enumerate(opts[:5], 1)
        )
        await message.reply(
            f"<b>🔍 Options:</b>\n{choices}\n\nReply with the number:",
            parse_mode=ParseMode.HTML
        )
        return

# -------------------- Handle Number Reply --------------------
@app.on_message(filters.regex(r"^\d+$"))
async def handle_number_reply(client, message: Message):
    uid = message.from_user.id
    choice = int(message.text)

    # Details choice
    if movie_options.get(uid, {}).get("mode") == "details_choice":
        opts = movie_options[uid]["opts"]
        if choice < 1 or choice > len(opts):
            await message.reply("❌ <b>Invalid choice.</b>", parse_mode=ParseMode.HTML)
            return
        m = opts[choice - 1]
        poster_url = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
        title = m.get("title")
        overview = m.get("overview", "No description available.")
        rating = m.get("vote_average", "?")
        date = m.get("release_date", "?")
        language = m.get("original_language", "?").upper()

        # Fetch genre names
        genre_resp = requests.get(
            f"https://api.themoviedb.org/3/genre/movie/list",
            params={"api_key": TMDB_API_KEY}, timeout=10
        ).json().get("genres", [])
        genre_map = {g["id"]: g["name"] for g in genre_resp}
        genres = [genre_map.get(i) for i in m.get("genre_ids", []) if genre_map.get(i)]

        caption = (
            f"🎬 <b>{title}</b>\n"
            f"📅 <b>Release:</b> {date}\n"
            f"🌐 <b>Language:</b> {language}\n"
            f"⭐ <b>Rating:</b> {rating}/10\n"
            f"🎭 <b>Genres:</b> {', '.join(genres) if genres else 'N/A'}\n\n"
            f"📝 <i>{overview[:400]}</i>"
        )
        await client.send_photo(message.chat.id, photo=poster_url, caption=caption, parse_mode=ParseMode.HTML)
        movie_options.pop(uid, None)
        return

    # Original uploader number reply
    if uid in movie_options and "link" in movie_options[uid]:
        data = movie_options.pop(uid)
        opts = data["opts"]
        if choice < 1 or choice > len(opts):
            await message.reply("❌ <b>Invalid choice.</b>", parse_mode=ParseMode.HTML)
            return
        m = opts[choice - 1]
        title = m["title"]
        date = m.get("release_date", "?")
        link = data["link"]
        team = data["team"]
        img_url = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
        caption = (
            f"✨🎬 <b>{title} Latest Movie </b> ✨\n"
            f"📅 <i>Release Date:</i> <b>{date}</b>\n\n"
            f"🤩 <b>LOGIN & WATCH FULL MOVIE</b>\n"
            "──────────────────\n"
            f"🌐 <u>Language:</u> HINDI / ENGLISH / TAMIL\n\n"
            f"💕 <b>480P</b>\n{link}\n\n"
            f"💕 <b>720P</b>\n{link}\n\n"
            f"💕 <b>1080P</b>\n{link}\n\n"
            "──────────────────\n"
            f"🔔 <b>STAY UPDATED {team}</b>"
        )
        await client.send_photo(message.chat.id, img_url, caption=caption, parse_mode=ParseMode.HTML)
        link_flow_state.pop(uid, None)

if __name__ == "__main__":
    app.run()
