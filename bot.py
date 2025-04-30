import requests
from pyrogram import Client, filters
import logging
import time

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


def get_movie_poster(movie_name, min_year=2021):
    """Fetch movie poster from TMDB API filtering releases after `min_year - 1`."""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    retries = 3
    backoff_time = 2

    with requests.Session() as session:
        for attempt in range(retries):
            try:
                response = session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Iterate through results to find a release after the given year
                for movie in data.get("results", []):
                    release_date = movie.get("release_date", "")
                    if not release_date:
                        continue
                    release_year = release_date.split("-")[0]
                    try:
                        year = int(release_year)
                    except ValueError:
                        continue

                    if year >= min_year:
                        poster_path = movie.get("poster_path")
                        if poster_path:
                            title = movie.get("title")
                            return title, release_year, f"https://image.tmdb.org/t/p/w500{poster_path}"

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {e}")
                return None, None, None
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout error: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error (Attempt {attempt + 1}/{retries}): {e}")

            time.sleep(backoff_time)
            backoff_time *= 2

    return None, None, None


@app.on_message(filters.command("movielink"))
async def send_movie_link(client, message):
    """Handles the /movielink command and sends the movie poster with download links"""
    if len(message.command) < 3:
        await message.reply_text("Usage: `/movielink <movie name> <link>`")
        return

    movie_name = " ".join(message.command[1:-1])
    link = message.command[-1]
    movie_title, release_year, poster_url = get_movie_poster(movie_name, min_year=2021)

    if poster_url:
        caption = (
            f"**{movie_title}** **Latest Movie** **{release_year}**\n\n"
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

        await client.send_photo(
            message.chat.id,
            poster_url,
            caption=caption
        )
    else:
        await message.reply_text("Sorry, I couldn't find a movie released after 2020. 😔")


if __name__ == "__main__":
    app.run()
