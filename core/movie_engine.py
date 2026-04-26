import os
import asyncio
import logging
import requests
import json
import sqlite3
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from google import genai

# Config ဖိုင်ထဲက သော့များနှင့် ဆက်တင်များကို လှမ်းယူခြင်း
from config import Config

# ==========================================
# 📝 LOGGING SETUP (Professional ခြေရာခံစနစ်)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CORE_ENGINE")

# ==========================================
# 🗄️ DATABASE SETUP (Anti-Duplicate System)
# ==========================================
DB_FILE = "movies_memory.db"

def init_db():
    """ဇာတ်ကားဟောင်းများ မှတ်သားမည့် မှတ်ဉာဏ်တိုက် တည်ဆောက်ခြင်း"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS downloaded_movies (
                        tmdb_id INTEGER PRIMARY KEY,
                        title TEXT,
                        media_type TEXT,
                        target_channel TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_series_index(series_key: str):
    """Series ပိုစတာဟောင်း ရှိ/မရှိ နှင့် Data များ ရှာဖွေခြင်း"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS series_index (
                        series_key TEXT PRIMARY KEY, message_id INTEGER, buttons_data TEXT, series_data TEXT)''')
    try:
        cursor.execute("SELECT message_id, buttons_data, series_data FROM series_index WHERE series_key = ?", (series_key,))
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE series_index ADD COLUMN series_data TEXT")
        cursor.execute("SELECT message_id, buttons_data, series_data FROM series_index WHERE series_key = ?", (series_key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"message_id": result[0], "buttons_data": result[1], "series_data": result[2] if len(result)>2 else None}
    return None

def save_series_index(series_key: str, message_id: int, buttons_data: str, series_data: str = None):
    """Series ပိုစတာသစ်၏ Data များကို မှတ်သားခြင်း"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS series_index (
                        series_key TEXT PRIMARY KEY, message_id INTEGER, buttons_data TEXT, series_data TEXT)''')
    try:
        cursor.execute("INSERT OR REPLACE INTO series_index (series_key, message_id, buttons_data, series_data) VALUES (?, ?, ?, ?)", 
                       (series_key, message_id, buttons_data, series_data))
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE series_index ADD COLUMN series_data TEXT")
        cursor.execute("INSERT OR REPLACE INTO series_index (series_key, message_id, buttons_data, series_data) VALUES (?, ?, ?, ?)", 
                       (series_key, message_id, buttons_data, series_data))
    conn.commit()
    conn.close()    

def is_movie_downloaded(tmdb_id: int) -> bool:
    """TMDB ID ဖြင့် တင်ပြီးသားကား ဟုတ်/မဟုတ် တိတိကျကျ စစ်ဆေးခြင်း"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM downloaded_movies WHERE tmdb_id = ?", (tmdb_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result)    

def is_movie_title_downloaded(title: str) -> bool:
    """နာမည်ဖြင့် တင်ပြီးသားကား ဟုတ်/မဟုတ် အကြမ်းဖျင်းစစ်ဆေးခြင်း (Early Check)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM downloaded_movies WHERE title LIKE ?", (title.strip(),))
    result = cursor.fetchone()
    conn.close()
    return bool(result)

def mark_movie_downloaded(tmdb_id: int, title: str, media_type: str, target_channel: str):
    """တင်ပြီးသွားသော ကားများကို မှတ်ဉာဏ်ထဲ ထည့်သွင်းခြင်း"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO downloaded_movies (tmdb_id, title, media_type, target_channel) VALUES (?, ?, ?, ?)", 
                   (tmdb_id, title, media_type, target_channel))
    conn.commit()
    conn.close()

init_db() # စတင် Run သည်နှင့် Database အဆင်သင့်ဖြစ်ရမည်

# ==========================================
# 🤖 စက်ရုပ်များ အသင့်ပြင်ဆင်ခြင်း (Clients Setup)
# ==========================================
bot_app = Client("auto_publisher_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.TELEGRAM_TOKEN, ipv6=False)

async def start_core_clients():
    # Userbot (client) ကို Plugin ဘက်မှ နှိုးပေးမည်ဖြစ်၍ ဤနေရာတွင် Publisher Bot ကိုသာ နှိုးပါမည်။
    if not bot_app.is_connected:
        logger.info("🔄 Publisher Bot အား အသက်သွင်းနေပါသည်...")
        await bot_app.start()

# ==========================================
# 🧠 AI & ROUTING ENGINE (TMDB + Gemini)
# ==========================================
# --- [MAJOR UPDATE] Auto Retry System ---
def generate_ai_content_with_retry(model_name: str, prompt: str):
    """Gemini API ကို Key အလှည့်ကျဖြင့် Retry လုပ်ပေးမည့်စနစ်"""
    max_retries = 3
    for attempt in range(max_retries):
        current_key = Config.get_next_api_key()
        try:
            client = genai.Client(api_key=current_key)
            response = client.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception as e:
            logger.warning(f"⚠️ API Key Error (Attempt {attempt+1}/{max_retries}): {e}. နောက် Key တစ်ခုဖြင့် ထပ်ကြိုးစားပါမည်။")
            import time
            time.sleep(2) # ခဏနားမည်
            
    logger.error("❌ API Keys အားလုံး Fail သွားပါပြီ။")
    return None

# --- [MAJOR UPDATE] Tavily Web Search (Backup Plan) ---
def search_tavily_for_movie(query: str):
    """Tavily API ဖြင့် အင်တာနက်တစ်ခွင် ဇာတ်ကားအချက်အလက် ရှာဖွေခြင်း"""
    if not getattr(Config, 'TAVILY_API_KEY', None): return None
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": Config.TAVILY_API_KEY,
            "query": f"{query} movie or animation plot synopsis release year rating",
            "search_depth": "basic",
            "include_answer": True,
            "include_images": True,
            "max_results": 3
        }
        res = requests.post(url, json=payload).json()
        # စာသားရော၊ ပုံတွေပါ ၂ ခုလုံးကို ပြန်ပို့ပေးမည်
        return {
            "text": res.get("answer") or str(res.get("results", "")),
            "images": res.get("images", [])
        }
    except Exception as e:
        logger.error(f"❌ Tavily Error: {e}")
        return None    

def get_movie_data_auto(search_query: str):
    """Gemini AI (Validator) နှင့် TMDB ပေါင်းစပ်၍ အတိကျဆုံး ရှာဖွေမည့်စနစ်"""
    import json
    import re
    
    logger.info(f"🤖 AI (Step 1) ဖြင့် နာမည်နှင့် ခုနှစ်ကို ရှာဖွေနေပါသည်...")
    
    # ----------------------------------------------------
    # အဆင့် (၁): Keyword အကြမ်းဖျင်း ရှာဖွေခြင်း
    # ----------------------------------------------------
    step1_prompt = f"""You are a movie title extraction bot. 
Extract the clean English movie title, release year, season number, and episode number from the following text.
Rules:
1. The title is often hidden with symbols (e.g., Une*xpe*ct*ed Fa*m*ily). Remove symbols and return "Unexpected Family".
2. Ignore actor names (e.g., Jackie Chan), Myanmar text, emojis, links, and resolutions.
3. Detect TV Series info. "စီစဉ် ၂" or "Season 2" = Season 2. "အပိုင်း ၁" or "Ep 1" = Episode 1. If not a series, return null for season/episode.
4. Output MUST be ONLY a raw JSON object.

Text: {search_query}
Format: {{"title": "Movie Name", "year": "YYYY", "season": 2, "episode": 1}}"""

    ai_response_1 = generate_ai_content_with_retry('gemini-2.5-flash', step1_prompt)
    
    clean_name = search_query
    extracted_year = None
    extracted_season = None
    extracted_episode = None
    
    if ai_response_1:
        match = re.search(r'\{.*\}', ai_response_1, re.DOTALL)
        if match:
            try:
                ai_data = json.loads(match.group(0))
                clean_name = ai_data.get("title", search_query)
                extracted_year = str(ai_data.get("year", ""))
                if extracted_year in ["N/A", "None", ""]: extracted_year = None
                extracted_season = ai_data.get("season")
                extracted_episode = ai_data.get("episode")
            except: pass

    logger.info(f"🧹 AI Keyword ရလဒ်: '{clean_name}' (Year: {extracted_year}, S: {extracted_season}, E: {extracted_episode}) ဖြင့် TMDB တွင် ရှာပါမည်...")
    
    # --- [MAJOR UPDATE] Early Database Check (API သက်သာစေရန်) ---
    # [MAGIC FIX] Series အပိုင်းသစ်များ (Episode ပါလာလျှင်) Early Check ကို ကျော်ဖြတ်ခွင့်ပေးမည်
    if extracted_episode is None and is_movie_title_downloaded(clean_name):
        logger.warning(f"⚠️ '{clean_name}' သည် Database တွင် တင်ပြီးသားဖြစ်နေသဖြင့် ရပ်တန့်လိုက်ပါမည်။ (API Token များ သက်သာသွားပါပြီ)")
        return {"status": "already_exists", "title": clean_name} # အထူး Status ဖြင့် ပြန်ပို့မည်
    
    logger.info(f"🆕 အသစ်ဖြစ်ကြောင်း အကြမ်းဖျင်း အတည်ပြုပါသည်။ TMDB တွင် ဆက်လက်ရှာဖွေပါမည်...")

    # ----------------------------------------------------
    # အဆင့် (၂): TMDB မှ ထိပ်ဆုံး (၅) ကား ဆွဲယူခြင်း
    # ----------------------------------------------------
    search_url = "https://api.themoviedb.org/3/search/multi"
    selected_tmdb_id = None
    top_candidates = []
    
    try:
        res = requests.get(search_url, params={"api_key": Config.TMDB_API_KEY, "query": clean_name, "language": "en-US"}).json()
        results = [r for r in res.get('results', []) if r.get('media_type') in ['movie', 'tv']]

        if results:
            top_candidates = results[:5]
            candidates_text = ""
            for idx, item in enumerate(top_candidates):
                c_title = item.get('title') or item.get('name')
                c_year = item.get('release_date', '')[:4] or item.get('first_air_date', '')[:4]
                c_overview = item.get('overview', 'No overview available.')
                candidates_text += f"ID: {item['id']} | Title: {c_title} ({c_year}) | Overview: {c_overview}\n\n"

            logger.info(f"🔎 TMDB မှ ဇာတ်ကား ({len(top_candidates)}) ကား တွေ့ရှိပါသည်။ AI Validator ဖြင့် တိုက်စစ်ပါမည်...")

            step2_prompt = f"""You are a master movie judge. I will give you a Telegram post containing a movie description, and a list of {len(top_candidates)} candidate movies from TMDB.
Your ONLY job is to find the EXACT matching movie from the TMDB list based on the story/context in the Telegram post.

CRITICAL RULES: 
1. YEAR-LOCK: If the Telegram post explicitly mentions a release year (e.g., 2026), strictly match it.
2. TYPE-LOCK: Look at the "[Hint - Source Channel Name: ...]". If the channel name contains "Toon", "Cartoon", "Animation", or "Anime", you MUST prioritize the Animated version. If the channel name does NOT contain those, and the text does not explicitly say "Anime", you MUST prioritize the Live-Action TV Series version. Reject mismatches!

Telegram Post: {search_query}
TMDB Candidates:
{candidates_text}
Respond STRICTLY in JSON format.
If a matching movie is found: {{"tmdb_id": 12345}}
If NO movie matches the story context or year at all: {{"tmdb_id": null}}"""

            ai_response_2 = generate_ai_content_with_retry('gemini-2.5-flash', step2_prompt)
            
            if ai_response_2:
                match_2 = re.search(r'\{.*\}', ai_response_2, re.DOTALL)
                if match_2:
                    try:
                        validator_data = json.loads(match_2.group(0))
                        selected_tmdb_id = validator_data.get("tmdb_id")
                    except: pass
    except Exception as e:
        logger.error(f"TMDB Search Error: {e}")

    # ----------------------------------------------------
    # အဆင့် (၃): THE ULTIMATE BACKUP PLAN (Tavily + Ghost Post)
    # ----------------------------------------------------
    if not selected_tmdb_id:
        logger.warning("⚠️ TMDB တွင် မရှိပါ (သို့) Validator မှ ပယ်ချလိုက်ပါသည်။ Tavily Backup Plan စတင်ပါမည်...")
        
        # [MAGIC FIX] clean_name သို့မဟုတ် extracted_year တွင် None ပါလာပါက Crash မဖြစ်စေရန် ကာကွယ်ခြင်း
        safe_name = str(clean_name) if clean_name else "Unknown Movie"
        safe_year = str(extracted_year) if extracted_year else ""
        query_text = (safe_name + " " + safe_year).strip()
        
        tavily_results = search_tavily_for_movie(query_text)
        
        # [MAGIC FIX] Python hash() ပြောင်းလဲမှုကြောင့် ID လွဲပြီး ခလုတ်မတိုးသည့်ပြဿနာကို ဖြေရှင်းရန်
        import hashlib
        hash_str = clean_name.strip().lower()
        ghost_id = int(hashlib.md5(hash_str.encode('utf-8')).hexdigest(), 16) % 100000000
        
        if tavily_results and isinstance(tavily_results, dict):
            logger.info("🌐 Tavily မှ အချက်အလက်များ ရရှိပါသည်။ AI (Validator) ဖြင့် ဇာတ်လမ်းတိုက်စစ်ပြီး ဆွဲထုတ်ပါမည်...")
            
            t_text = tavily_results.get("text", "")
            t_images = tavily_results.get("images", [])
            
            tavily_prompt = f"""You are a master movie researcher. I will provide a Telegram post (Myanmar language) describing a movie, some Web Search Results, and Image URLs.
Your job is to deeply analyze the Telegram post's story, find the EXACT matching movie from the Web Search Results, and extract its details. 

CRITICAL IMAGE RULES:
Select ONLY a direct image URL ending in .jpg or .png from the Image URLs list. Do NOT select .webp, .svg, or links from protected CDNs. If no valid direct .jpg/.png URL is found, return "None".

CRITICAL TYPE RULE: 
Look at the "[Hint - Source Channel Name: ...]". If the channel name contains "Toon", "Cartoon", "Animation", or "Anime", you MUST set "is_animation": true. Otherwise, if it does not explicitly say "Anime" in the post text, you MUST set "is_animation": false. Do not guess based on the franchise name alone.

Telegram Post:
{search_query}

Web Search Results:
{t_text}

Image URLs:
{t_images}

Return ONLY a valid JSON format: {{"title": "Clean Movie Name", "year": "YYYY", "overview": "Short english summary of the plot", "rating": 7.5, "poster_url": "selected_image_url", "is_animation": true_or_false, "media_type": "movie_or_tv", "genres": ["Action", "Sci-Fi"]}}
If you absolutely cannot find a matching movie, extract the best logical guess based on the Telegram post."""
            
            tavily_ai_res = generate_ai_content_with_retry('gemini-2.5-flash', tavily_prompt)
            try:
                t_match = re.search(r'\{.*\}', tavily_ai_res, re.DOTALL)
                t_data = json.loads(t_match.group(0))
                
                # အကယ်၍ AI ပေးသောပုံသည် None ဖြစ်နေပါက သို့မဟုတ် လင့်ခ်အမှားဖြစ်ပါက Dummy ပုံကို ပြောင်းသုံးမည်
                ai_poster = str(t_data.get("poster_url", ""))
                if ai_poster.startswith("http") and "none" not in ai_poster.lower():
                    final_poster = ai_poster
                else:
                    final_poster = "https://dummyimage.com/500x750/1a1a1a/ffffff.jpg&text=No+Poster+Available"
                
                # [MAJOR UPDATE] Ghost Post များအတွက် Channel Auto ခွဲခြားခြင်း
                is_animation = t_data.get("is_animation", False)
                t_media_type = t_data.get("media_type", "movie")
                
                if is_animation:
                    target_channel = "THUKHA_CARTOONS"
                elif t_media_type == "tv":
                    target_channel = "THUKHA_SERIES"
                else:
                    target_channel = "THUKHA_MOVIES"
                
                # [MAGIC FIX] Rating နေရာတွင် null (None) ပါလာပါက Error မတက်စေရန် ကာကွယ်ခြင်း
                raw_rating = t_data.get("rating", 0.0)
                try:
                    safe_rating = float(raw_rating) if raw_rating is not None else 0.0
                except (ValueError, TypeError):
                    safe_rating = 0.0

                # [MAGIC FIX] TMDB ပုံစံအတိုင်း Hashtags များကို အတိအကျ ဖန်တီးခြင်း
                t_title = t_data.get("title", clean_name)
                t_year = str(t_data.get("year", extracted_year or "N/A"))
                
                t_genres = t_data.get("genres", [])
                if not isinstance(t_genres, list): t_genres = []
                base_hashtags = " ".join([f"#{g.replace(' ', '').replace('-', '')}" for g in t_genres])
                
                clean_title_hash = t_title.replace(" ", "").replace(":", "").replace("-", "").replace("'", "").lower()
                extra_tags = f"#{clean_title_hash} #Y{t_year}" if t_year != 'N/A' and t_year.isdigit() else f"#{clean_title_hash}"
                final_hashtags = f"{base_hashtags} {extra_tags}".strip()

                logger.info(f"✅ Tavily မှ တိုက်စစ်ပြီး '{t_title}' ကို အောင်မြင်စွာ ရရှိပါသည်။ Ghost Post အဖြစ် {target_channel} သို့ တင်ပါမည်။")
                return {
                    "tmdb_id": ghost_id, "media_type": t_media_type, "target_channel": target_channel,
                    "title": t_title, "year": t_year, 
                    "hashtags": final_hashtags,
                    "rating": safe_rating,
                    "poster_url": final_poster,
                    "overview": t_data.get("overview", "No overview found."),
                    "season": extracted_season, 
                    "episode": extracted_episode
                }
            except Exception as e:
                logger.error(f"⚠️ Tavily Data Parse Error: {e}")
        
        # Tavily လည်း မရရင် (Ultimate Fallback - Local Myanmar Movie)
        logger.warning("⚠️ Tavily တွင်လည်း မရှိပါ။ (Local ကားဖြစ်နိုင်ပါသည်) Basic Ghost Post အဖြစ် တင်ပါမည်။")
        
        # Local ပို့စ်အတွက်လည်း TMDB ပုံစံအတိုင်း Hashtag ပြင်ဆင်ခြင်း
        local_year = extracted_year if extracted_year else "N/A"
        clean_title_hash_local = clean_name.replace(" ", "").replace(":", "").replace("-", "").replace("'", "").lower()
        local_tags = f"#{clean_title_hash_local} #Y{local_year}" if local_year != 'N/A' and local_year.isdigit() else f"#{clean_title_hash_local}"
        
        return {
            "tmdb_id": ghost_id, "media_type": "movie", "target_channel": "THUKHA_MOVIES",
            "title": clean_name.title(), "year": local_year,
            "hashtags": local_tags,
            "rating": 0.0,
            "poster_url": "https://dummyimage.com/500x750/1a1a1a/ffffff.jpg&text=No+Poster+Available",
            "overview": "ဤဇာတ်ကား၏ အချက်အလက်များကို အင်တာနက်တွင် ရှာမတွေ့ပါ။ မူရင်းပို့စ်ပါ အညွှန်းကိုသာ အသုံးပြုပါ။",
            "season": extracted_season, 
            "episode": extracted_episode
        }

    # ----------------------------------------------------
    # အဆင့် (၄): TMDB မှ ရွေးချယ်ထားသော ID အစစ် ဖြင့် Data ယူခြင်း
    # ----------------------------------------------------
    logger.info(f"🎯 AI Validator မှ အတိကျဆုံး ဇာတ်ကား (TMDB ID: {selected_tmdb_id}) ကို ရွေးချယ်ပေးလိုက်ပါသည်!")
    media_type = next((item['media_type'] for item in top_candidates if item.get('id') == selected_tmdb_id), 'movie')
    
    try:
        detail_url = f"https://api.themoviedb.org/3/{media_type}/{selected_tmdb_id}?api_key={Config.TMDB_API_KEY}&language=en-US"
        details = requests.get(detail_url).json()

        title = details.get('title') if media_type == 'movie' else details.get('name')
        date_key = 'release_date' if media_type == 'movie' else 'first_air_date'
        year = details.get(date_key, 'N/A')[:4]
        genres = [g['name'] for g in details.get('genres', [])]
        
        if "Animation" in genres: target_channel = "THUKHA_CARTOONS"
        elif media_type == "tv": target_channel = "THUKHA_SERIES"
        else: target_channel = "THUKHA_MOVIES"

        base_hashtags = " ".join([f"#{g.replace(' ', '')}" for g in genres])
        clean_title_hash = title.replace(" ", "").replace(":", "").replace("-", "").replace("'", "").lower()
        extra_tags = f"#{clean_title_hash} #Y{year}" if year != 'N/A' else f"#{clean_title_hash}"
        
        return {
            "tmdb_id": selected_tmdb_id, "media_type": media_type, "target_channel": target_channel,
            "title": title, "year": year, "hashtags": f"{base_hashtags} {extra_tags}",
            "rating": round(details.get('vote_average', 0), 1),
            "poster_url": f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}" if details.get('poster_path') else "https://via.placeholder.com/500x750/1a1a1a/ffffff?text=No+Poster",
            "overview": details.get('overview', "ဇာတ်လမ်းအကျဉ်း မရရှိနိုင်ပါ။"),
            "season": extracted_season, 
            "episode": extracted_episode
        }
    except Exception as api_e:
        logger.error(f"TMDB Details Error: {api_e}")
        return None

# ==========================================
# 🎬 THE MASTER PIPELINE (အဓိက အသက်သွေးကြော)
# ==========================================
async def process_and_publish_movie(client, source_message, raw_file_name, pre_fetched_data=None):
    
    await start_core_clients()
    movie_name = raw_file_name if raw_file_name else "Unknown Movie"
    
    # [MAGIC FIX] Source Channel အမည်ကို AI ထံ Hint အဖြစ် ပေးပို့မည် (ကာတွန်း/လူကား အလိုလိုခွဲရန်)
    channel_hint = source_message.chat.title if source_message and getattr(source_message, 'chat', None) else "Unknown Channel"
    movie_query_with_hint = f"{movie_name}\n[Hint - Source Channel Name: '{channel_hint}']"
    
    # ၁။ Data အရင်ယူမည် (ဒီနေရာတွင် Gemini ကို နာမည်ခွဲထုတ်ရန်သာ သုံးထားသည်)
    data = pre_fetched_data if pre_fetched_data else await asyncio.to_thread(get_movie_data_auto, movie_query_with_hint)
    if not data:
        return False

    # [MAJOR UPDATE] Early Check မှ တင်ပြီးသားဟု ဆိုလာလျှင် ချက်ချင်းရပ်မည်
    if data.get("status") == "already_exists":
        logger.warning(f"⚠️ ဤဇာတ်ကား/Series '{data.get('title')}' အား တင်ပြီးသားဖြစ်သဖြင့် ကျော်သွားပါမည် (Skipped). Token Saved!")
        return False 

    tmdb_id = data["tmdb_id"]
    target_channel = data["target_channel"]
    season = data.get("season")
    episode = data.get("episode")

    # [MAGIC FIX] Series များအတွက် DB တွင် ID မထပ်စေရန် Unique ID (Pseudo-ID) ဖန်တီးခြင်း
    db_check_id = tmdb_id
    if target_channel == "THUKHA_SERIES" and episode is not None:
        try:
            # ဥပမာ - TMDB ID 110011, Season 2, Episode 1 ဆိုလျှင် 1100110201 အဖြစ်ပြောင်းမှတ်မည်
            s_num = int(season) if season else 1
            e_num = int(episode)
            db_check_id = int(f"{tmdb_id}{s_num:02d}{e_num:02d}")
        except (ValueError, TypeError):
            pass

    # ၂။ [MAJOR UPDATE] DB ကို အရင်စစ်မည်။
    if is_movie_downloaded(db_check_id):
        logger.warning(f"⚠️ ဤဇာတ်ကား/Series '{data['title']}' အား တင်ပြီးသားဖြစ်သဖြင့် ကျော်သွားပါမည် (Skipped). Token Saved!")
        return True 

    # ၃။ Config စစ်ဆေးခြင်း
    target_config = Config.CHANNELS_CONFIG.get(target_channel)
    if not target_config: return False

    # ၄။ Storage သို့ Copy တင်ခြင်း
    logger.info(f"✅ အသစ်ဖြစ်ကြောင်း အတည်ပြုပြီးပါပြီ။ {target_channel} သို့ တိုက်ရိုက် Copy ကူးပါမည်...")
    try:
        sent_msg = await client.copy_message(chat_id=target_config["storage_id"], from_chat_id=source_message.chat.id, message_id=source_message.id, caption="Copying...")
    except FloodWait as e:
        await asyncio.sleep(e.value + 2)
        sent_msg = await client.copy_message(chat_id=target_config["storage_id"], from_chat_id=source_message.chat.id, message_id=source_message.id, caption="Copying...")
    except Exception as e:
        logger.error(f"❌ Copy ကူးရာတွင် Error ဖြစ်သွားပါသည်: {e}")
        sent_msg = None
    
    if not sent_msg: return False

    storage_msg_id = sent_msg.id
    # Storage ပို့စ်တွင် အပိုင်းစဉ် ပေါ်စေရန်
    storage_title = f"{data['title']} ({data['year']})"
    if target_channel == "THUKHA_SERIES" and episode is not None:
        s_text = f"Season {season}" if season else "Season 1"
        storage_title = f"{data['title']} ({data['year']}) - {s_text} : Episode {episode}"
        
    await sent_msg.edit_text(f"{storage_title}\n\nStorage ID: {storage_msg_id}")

    # --- [SMART EDIT LOGIC] Series Index ကို ကြိုတင်စစ်ဆေးခြင်း ---
    # Channel နာမည်ကို မစစ်တော့ဘဲ အပိုင်းပါတာနဲ့ Series အဖြစ် အလိုလို သတ်မှတ်မည်
    is_series = (episode is not None)
    existing_index = None
    if is_series:
        series_key = f"{tmdb_id}_{season if season else 1}"
        existing_index = get_series_index(series_key)

    # ၅။ [MAJOR UPDATE] အပိုင်း (၂) ဖြစ်လျှင် Data အဟောင်းကို ပြန်သုံး၍ AI Token ချွေတာမည်
    if is_series and existing_index and existing_index.get("series_data"):
        logger.info("⚡ Series အဟောင်းဖြစ်သဖြင့် Gemini ကို မသုံးတော့ဘဲ မှတ်ဉာဏ်ထဲမှ အကျဉ်းချုပ်ကို ပြန်သုံးပါမည်...")
        cached_data = json.loads(existing_index["series_data"])
        data['synopsis'] = cached_data.get('synopsis', data['overview'])
        data['poster_url'] = cached_data.get('poster_url', data['poster_url'])
        data['hashtags'] = cached_data.get('hashtags', data['hashtags'])
    else:
        logger.info("🤖 တင်ရန် သေချာသွားပြီဖြစ်သဖြင့် Gemini ဖြင့် Cinematic အကျဉ်းချုပ် ဖန်တီးနေပါသည်...")
        try:
            prompt = f"""You are an expert movie reviewer writing for a Myanmar audience on a popular Telegram channel.
            Rewrite and translate the following movie synopsis into an exciting, engaging, and cinematic Burmese language. 
            CRITICAL INSTRUCTION: Maximum 5 to 7 sentences. Strictly under 600 characters.
            Synopsis: {data['overview']}"""

            # Retry စနစ်ဖြင့် ဘာသာပြန်ခိုင်းခြင်း
            ai_translation = generate_ai_content_with_retry('gemini-3-flash-preview', prompt)
            mm_synopsis = ai_translation.strip() if ai_translation else data['overview']
            if len(mm_synopsis) > 700: mm_synopsis = mm_synopsis[:700] + "..." 
        except Exception as ai_e:
            logger.error(f"⚠️ Gemini Translation Error: {ai_e}")
            mm_synopsis = data['overview']
            
        data['synopsis'] = mm_synopsis # ဘာသာပြန်ပြီးသားစာကို Data ထဲ ပြန်ထည့်မည်

    # ၆။ Publisher Bot ဖြင့် Public Channel ပေါ်သို့ တင်ခြင်း
    logger.info("🚀 Publisher Bot ဖြင့် Public Channel သို့ လှမ်းတင်နေပါပြီ...")
    
    # [MAGIC FIX] Rating 0.0 ဖြစ်နေပါက IMDb စာကြောင်းကို လုံးဝ ဖျောက်ချမည့်စနစ်
    rating_val = data.get('rating', 0.0)
    rating_line = f"IMDb Rating: ⭐ {rating_val}/10\n" if rating_val > 0.0 else ""
    
    # [MAGIC FIX] Series ဖြစ်လျှင် Caption တွင် Season နှင့် Episode လှလှပပ ထည့်ပေးရန် (Channel နာမည်ကို မစစ်တော့ပါ)
    title_header = f"**{data['title']} ({data['year']})**"
    if is_series:
        s_text = f"Season {season}" if season else "Season 1"
        title_header = f"**{data['title']} ({data['year']}) - {s_text} : Episode {episode}**"
    
    caption_text = f"""{title_header}\n\n{rating_line}Subtitle: Myanmar Sub (မြန်မာစာတန်းထိုး)\n\nဇာတ်လမ်းအကျဥ်း:\n{data['synopsis']}\n\nရိုက်ရှာရန် hashtag များ:\n{data['hashtags']}\n\n#credit_to_original_owner\n━━━━━━━━━━━━━━━━\nကြည့်ရှုရန် အောက်ပါ Button များကို နှိပ်ပါ။ 👇"""

    clean_storage_id = str(target_config["storage_id"]).replace("-100", "")
    watch_link = f"https://t.me/c/{clean_storage_id}/{storage_msg_id}"
    
    if is_series:
        series_key = f"{tmdb_id}_{season if season else 1}"
        existing_index = get_series_index(series_key)
        new_button = {"text": f"Ep {episode}", "url": watch_link}
        
        if existing_index:
            ep_buttons_data = json.loads(existing_index["buttons_data"])
            ep_buttons_data.append(new_button)
        else:
            ep_buttons_data = [new_button]
            
        # ခလုတ်များကို ၃ ခု တစ်တန်း စီစဉ်မည်
        ep_inline_buttons = [InlineKeyboardButton(b["text"], url=b["url"]) for b in ep_buttons_data]
        ep_rows = [ep_inline_buttons[i:i + 3] for i in range(0, len(ep_inline_buttons), 3)]
        
        buttons_layout = [[InlineKeyboardButton("Channel အရင် Join ရန်နှိပ်ပါ 🔐", url=target_config["invite_link"])]]
        buttons_layout.extend(ep_rows)
    else:
        # ရိုးရိုး Movie အတွက် ခလုတ်
        buttons_layout = [[InlineKeyboardButton("Channel အရင် Join ရန်နှိပ်ပါ 🔐", url=target_config["invite_link"])], [InlineKeyboardButton("ဇာတ်ကားကြည့်ရန်နှိပ်ပါ 📥", url=watch_link)]]

    # Promo ခလုတ်များ ရှိပါက အောက်ဆုံးတွင် ထည့်မည်
    if "cross_promo_buttons" in target_config:
        promo_row = []
        for btn_list in target_config["cross_promo_buttons"]:
            for btn in btn_list: promo_row.append(InlineKeyboardButton(btn["text"], url=btn["url"]))
        buttons_layout.append(promo_row)

    try:
        if is_series and existing_index:
            # ၁။ Series အဟောင်းဖြစ်လျှင် ပိုစတာဟောင်းကို Edit သွားလုပ်မည်
            main_msg_id = existing_index["message_id"]
            await bot_app.edit_message_reply_markup(
                chat_id=target_config["main_channel_id"],
                message_id=main_msg_id,
                reply_markup=InlineKeyboardMarkup(buttons_layout)
            )
            logger.info(f"🎉 Series ပိုစတာဟောင်း (ID: {main_msg_id}) တွင် အပိုင်း {episode} ကို အောင်မြင်စွာ တိုးပေးလိုက်ပါပြီ!")
            
            # ၂။ Notification ပေးမည် (ပိုစတာဟောင်းဆီသို့ Reply တွဲလျက်သား)
            noti_text = f"📢 **{data['title']}**\n\nအပိုင်းသစ် (Episode {episode}) ထွက်ပါပြီ! 🎉\nမူရင်းပိုစတာရှိ ခလုတ်များတွင် သွားရောက်ကြည့်ရှုနိုင်ပါပြီ။ 👇"
            await bot_app.send_message(
                chat_id=target_config["main_channel_id"], text=noti_text,
                reply_to_message_id=main_msg_id, disable_notification=False
            )
            
            # ၃။ DB သို့ ပြန်လည်မှတ်တမ်းတင်မည်
            save_series_index(series_key, main_msg_id, json.dumps(ep_buttons_data), json.dumps(data))
            mark_movie_downloaded(db_check_id, data['title'], data['media_type'], target_channel)

        else:
            # Movie (သို့) Series အပိုင်း (၁) အသစ်ဖြစ်လျှင် ပုံမှန်အတိုင်း ပိုစတာတင်မည်
            sent_post = await bot_app.send_photo(chat_id=target_config["main_channel_id"], photo=data['poster_url'], caption=caption_text, reply_markup=InlineKeyboardMarkup(buttons_layout))
            logger.info(f"🎉 Public Channel ({target_config['main_channel_id']}) ပေါ်သို့ အောင်မြင်စွာ တင်ပို့ပြီးပါပြီ!")
            
            if is_series:
                save_series_index(series_key, sent_post.id, json.dumps(ep_buttons_data), json.dumps(data))
            mark_movie_downloaded(db_check_id, data['title'], data['media_type'], target_channel)

    except Exception as bot_err:
        logger.warning(f"⚠️ ပိုစတာတင်/ပြင်ရာတွင် Error ဖြစ်နေသည် ({bot_err})။")
        try:
            # အကယ်၍ ပို့စ်အသစ်တင်ရာတွင် ပုံမှား၍ Error တက်ပါက Dummy ဖြင့် ထပ်တင်မည်
            if not (is_series and existing_index):
                fallback_poster = "https://dummyimage.com/500x750/1a1a1a/ffffff.jpg&text=No+Poster+Available"
                sent_post = await bot_app.send_photo(chat_id=target_config["main_channel_id"], photo=fallback_poster, caption=caption_text, reply_markup=InlineKeyboardMarkup(buttons_layout))
                if is_series:
                    save_series_index(series_key, sent_post.id, json.dumps(ep_buttons_data), json.dumps(data))
                mark_movie_downloaded(db_check_id, data['title'], data['media_type'], target_channel)
                logger.info(f"🎉 အရန်စနစ်ဖြင့် အောင်မြင်စွာ တင်ပို့ပြီးပါပြီ!")
        except Exception as retry_err:
            logger.error(f"❌ Main Channel သို့ တင်ရာတွင်လုံးဝ Error ဖြစ်နေသည်: {retry_err}")
            return False
    return True


# ==========================================
# 🛠️ MOVIE ENGINE ကို သီးသန့် စမ်းသပ်မည့် အပိုင်း
# ==========================================
if __name__ == "__main__":
    async def run_engine_test():
        import asyncio
        from pyrogram import Client
        from config import Config
        print("🚀 Core Engine Test Run စတင်နေပါပြီ...")
        
        # Publisher Bot ကို အသက်သွင်းမည်
        await start_core_clients()
        
        # ⚠️ ဒီနေရာမှာ မင်းစမ်းချင်တဲ့ Monitor Channel ID နဲ့ Message ID ကို ပြင်ထည့်ပါ
        TEST_CHANNEL_ID = -1003519309429 
        TEST_MESSAGE_ID = 539            
        
        # 🌟 Test Run အတွက် Gateway Session ကို ယာယီ လှမ်းသုံးပါမည်
        app = Client("jarvis_secretary", api_id=Config.API_ID, api_hash=Config.API_HASH, workdir="memory")
        await app.start()
        
        try:
            # --- [MAGIC FIX 0] Source Channel ကို မှတ်ဉာဏ်ထဲ အရင်ထည့်ခြင်း ---
            print(f"🔄 Source Channel ID ({TEST_CHANNEL_ID}) ကို တိုက်ရိုက် ချိတ်ဆက်နေပါသည်...")
            try:
                await app.get_chat(TEST_CHANNEL_ID)
            except Exception as e:
                print(f"⚠️ Source Channel ကို တိုက်ရိုက်ယူ၍မရပါ။ Dialogs မှတ်ဉာဏ်ကို အတင်းခေါ်ပါမည်... (Error: {e})")
                async for _ in app.get_dialogs():
                    pass 
            
            # --- [MAGIC FIX 1] Storage Channel များကိုပါ မှတ်ဉာဏ်ထဲ ထည့်ခြင်း ---
            print("🔄 Storage Channel များကို မှတ်ဉာဏ်ထဲ ကြိုတင်ထည့်သွင်းနေပါသည်...")
            for channel_name, config in Config.CHANNELS_CONFIG.items():
                try:
                    await app.get_chat(config["storage_id"])
                    print(f"✅ {channel_name} Storage ကို မှတ်ဉာဏ်ထဲ ထည့်ပြီးပါပြီ။")
                except Exception as e:
                    print(f"⚠️ {channel_name} ကို တိုက်ရိုက်ယူ၍မရပါ။ (Error: {e})")

            # ၁။ Message အစစ်ကို Telegram ကနေ လှမ်းယူခြင်း
            test_msg = await app.get_messages(TEST_CHANNEL_ID, TEST_MESSAGE_ID)
            
            # ၂။ အင်ဂျင်ထဲကို ထည့်ပြီး Run ကြည့်ခြင်း
            if getattr(test_msg, 'video', None) or getattr(test_msg, 'document', None):
                print(f"🎬 ဇာတ်ကားဖိုင် တွေ့ပါသည်၊ Engine ထဲသို့ တိုက်ရိုက်ပို့နေပါပြီ...")
                
                media_obj = test_msg.video if test_msg.video else test_msg.document
                
                # --- [MAJOR UPDATE] AI ကို Context အပြည့်အစုံ ပေးဖတ်မည့်စနစ် ---
                raw_target_text = ""
                
                if test_msg.caption:
                    raw_target_text += f"[Video Caption]: {test_msg.caption}\n"
                
                for offset in [1, 2]:
                    try:
                        prev_msg = await app.get_messages(TEST_CHANNEL_ID, TEST_MESSAGE_ID - offset)
                        if prev_msg.caption:
                            raw_target_text += f"[Post ID-{offset} Caption]: {prev_msg.caption}\n"
                        elif prev_msg.text:
                            raw_target_text += f"[Post ID-{offset} Text]: {prev_msg.text}\n"
                    except Exception:
                        pass
                    
                if not raw_target_text.strip():
                    raw_target_text = getattr(media_obj, 'file_name', "Unknown File")
                    
                print("\n💡 AI ထံသို့ ခွဲခြမ်းစိတ်ဖြာရန် ပို့ဆောင်နေပါသည်...")
                
                # 🌟 [အရေးကြီးဆုံး ပြင်ဆင်ချက်] `app` (client) ကို Parameter အဖြစ် ထည့်ပေးရပါမည်
                await process_and_publish_movie(app, test_msg, raw_file_name=raw_target_text)
                
                print("✅ Test Run အောင်မြင်စွာ ပြီးဆုံးပါပြီ! (Storage နဲ့ Public Channel တွေကို သွားစစ်ကြည့်ပါ)")
            else:
                print("❌ အဆိုပါ ID တွင် ဇာတ်ကားဖိုင် မရှိပါ။ Message ID အမှန် ပြန်စစ်ပါ။")
                
        except Exception as e:
            print(f"❌ Test Run တွင် Error တက်နေပါသည်: {e}")
        finally:
            await app.stop() # Test ပြီးလျှင် Session ပြန်ပိတ်ပေးမည်
            
    # Event Loop ဖြင့် Run ခြင်း
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_engine_test())