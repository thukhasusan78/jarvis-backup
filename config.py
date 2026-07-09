import os
from dotenv import load_dotenv
from itertools import cycle
import pytz

os.environ["http_proxy"] = "socks5://127.0.0.1:40000"
os.environ["https_proxy"] = "socks5://127.0.0.1:40000"
os.environ["all_proxy"] = "socks5://127.0.0.1:40000"

os.environ["NO_PROXY"] = "api.telegram.org,telegram.org,core.telegram.org,127.0.0.1,localhost"
os.environ["no_proxy"] = "api.telegram.org,telegram.org,core.telegram.org,127.0.0.1,localhost"

# .env ဖိုင်ထဲက အချက်အလက်တွေကို ဆွဲယူခြင်း
load_dotenv()

class Config:
    # --- 🤖 Identity ---
    BOT_NAME = os.getenv("BOT_NAME", "Jarvis")
    VERSION = "2.1.0 (Money Maker Build)"
    
    # --- 🧠 AI Brain Configuration ---
    # ငွေရှာမယ့် Agent ဖြစ်လို့ အမြန်ဆုံးနဲ့ စရိတ်အသက်သာဆုံး Model ကို သုံးမယ်
    MODEL_NAME = "gemini-2.5-flash" 

    SMART_MODEL_NAME = "gemini-3-flash-preview" # Orbit ရဲ့ 3 Pro ကို သုံးမယ်

    # --- VOICE CONFIG ---
    VOICE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

    VOICE_NAME = "Enceladus"
    
    # --- 🌌 Orbit Provider API Settings ---
    ORBIT_API_KEY = os.getenv("ORBIT_API_KEY") 
    QA_MODEL_NAME = "gemini-claude-opus-4-6-thinking"
    ORBIT_BASE_URL = "https://api.orbit-provider.com/cliproxy-api/api/provider/agy"
    
    # API Keys Management (Round Robin System)
    _keys_str = os.getenv("GEMINI_API_KEYS", "")
    if not _keys_str:
        # Key မထည့်ရသေးရင် Warning ပေးမယ်
        print("⚠️  WARNING: GEMINI_API_KEYS not found in .env")
        API_KEYS = []
    else:
        # ကော်မာ (,) ခံထားတဲ့ Key တွေကို ခွဲထုတ်ပြီး စာရင်းလုပ်မယ်
        API_KEYS = [k.strip() for k in _keys_str.split(",") if k.strip()]
    
    # Key တွေကို အလှည့်ကျ ယူသုံးဖို့ Cycle လုပ်ထားမယ်
    _key_cycle = cycle(API_KEYS) if API_KEYS else None

    @classmethod
    def get_next_api_key(cls):
        """Next available API key ကို ထုတ်ပေးမယ့် Function"""
        if not cls._key_cycle:
            raise ValueError("❌ No API Keys available! Check your .env file.")
        return next(cls._key_cycle)

    # --- 📡 Connectivity ---
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@thukhatech")
    TAVILY_KEY = os.getenv("TAVILY_KEY")
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", 0))

    # --- 💾 Memory Paths ---
    # Chat History သိမ်းမယ့် SQLite DB
    MEMORY_DB_PATH = os.path.join("memory", "jarvis_chat.db")
    # --- 🏢 Unified Vector Memory (ChromaDB) ---
    CHROMA_DB_PATH = os.path.join("memory", "chroma_db")
    EMBEDDING_MODEL = "models/gemini-embedding-001"
    
    CHROMA_BUSINESS_COLLECTION = "business_facts"  # For Secretary
    CHROMA_KNOWLEDGE_COLLECTION = "ceo_knowledge"  # For Main CEO Agent
    
    CHROMA_TOP_K = 5
    CHROMA_DISTANCE_THRESHOLD = 0.35

    # --- 🏢 Business RAG Memory (ChromaDB) ---
    CHROMA_BUSINESS_PATH = os.path.join("memory", "chroma_business")
    EMBEDDING_MODEL = "models/gemini-embedding-001"
    CHROMA_COLLECTION = "business_facts"
    CHROMA_TOP_K = 5
    CHROMA_DISTANCE_THRESHOLD = 0.35

    # --- 🦊 Browser / Search Settings ---
    # RAM 2GB VPS ဖြစ်လို့ Headless (မျက်နှာပြင်မပေါ်) ပဲ run မယ်
    HEADLESS_BROWSER = True
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    # --- ⚙️ Server Config ---
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    TIMEZONE = pytz.timezone('Asia/Yangon')

    # ==========================================
    # 🔐 USERBOT / PYROGRAM CONFIGS
    # ==========================================
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")

    # ==========================================
    # 🎬 MOVIE BOT CONFIGURATIONS
    # ==========================================
    TMDB_API_KEY = os.getenv("TMDB_API_KEY") 
    TAVILY_API_KEY = os.getenv("TAVILY_KEY")

# Auto-Monitor မှ ၂၄ နာရီ စောင့်ကြည့်ရမည့် သူများ၏ Channel ID များ
# ID: -1002861107636  =>  Name: နိုင်ငံခြားအက်ရှင်ဇာတ်ကားကောင်းများ
# ID: -1002177243316  =>  Name: မြန်မာစာတန်းထိုးဇာတ်ကားများ (CH)
# ID: -1003519309429  =>  Name: 𝗧𝗼𝗼𝗻𝗩𝗶𝗹𝗹𝗲
# ID: -1002496408921  =>  Name: မြန်မာစာတန်းထိုးဇာတ်ကားစုံ
# ID: -1003542479604  =>  Name: TZ Movies(Hollywood)
# ID: -1003334073150  =>  Name: Rabit Movie 
    MONITOR_CHANNELS = [-1002861107636, -1002177243316, -1003519309429, -1002496408921, -1003542479604, -1003334073150, -1003824267490] 

    CHANNELS_CONFIG = {
        "THUKHA_MOVIES": {
            "main_channel_id": "@thukhamovies",          
            "storage_id": -1003548493405,                
            "invite_link": "https://t.me/+SvLAsuIFfx1kN2Vl",
            "cross_promo_buttons": [
                [{"text": "📺 Series Channel", "url": "https://t.me/thukhaseries"}],
                [{"text": "🧸 Cartoons Channel", "url": "https://t.me/thukhacartoons"}]
            ]
        },
        "THUKHA_SERIES": {
            "main_channel_id": "@thukhaseries",          
            "storage_id": -1003564993052,                
            "invite_link": "https://t.me/+JwSYk3ntyZczYWI1",
            "cross_promo_buttons": [
                [{"text": "🎬 Movies Channel", "url": "https://t.me/thukhamovies"}],
                [{"text": "🧸 Cartoons Channel", "url": "https://t.me/thukhacartoons"}]
            ]
        },
        "THUKHA_CARTOONS": {
            "main_channel_id": "@thukhacartoons",        
            "storage_id": -1003824661116,                
            "invite_link": "https://t.me/+YiQ_pMMPq6ZjMDll",
            "cross_promo_buttons": [
                [{"text": "🎬 Movies Channel", "url": "https://t.me/thukhamovies"}],
                [{"text": "📺 Series Channel", "url": "https://t.me/thukhaseries"}]
            ]
        }
    }

# Folder တွေ မရှိရင် အလိုအလျောက် ဆောက်ပေးမယ့် code
os.makedirs("memory", exist_ok=True)