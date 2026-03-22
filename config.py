import os
from dotenv import load_dotenv
from itertools import cycle
import pytz

os.environ["http_proxy"] = "socks5://127.0.0.1:40000"
os.environ["https_proxy"] = "socks5://127.0.0.1:40000"
os.environ["all_proxy"] = "socks5://127.0.0.1:40000"

# .env ဖိုင်ထဲက အချက်အလက်တွေကို ဆွဲယူခြင်း
load_dotenv()

class Config:
    # --- 🤖 Identity ---
    BOT_NAME = os.getenv("BOT_NAME", "Jarvis")
    VERSION = "2.1.0 (Money Maker Build)"
    
    # --- 🧠 AI Brain Configuration ---
    # ငွေရှာမယ့် Agent ဖြစ်လို့ အမြန်ဆုံးနဲ့ စရိတ်အသက်သာဆုံး Model ကို သုံးမယ်
    MODEL_NAME = "gemini-3.1-flash-lite-preview" 

    SMART_MODEL_NAME = "gemini-3-flash-preview" # Orbit ရဲ့ 3 Pro ကို သုံးမယ်
    
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
    # Knowledge Base သိမ်းမယ့် Vector DB
    VECTOR_DB_PATH = os.path.join("memory", "knowledge_lance")

    # --- 🦊 Browser / Search Settings ---
    # RAM 2GB VPS ဖြစ်လို့ Headless (မျက်နှာပြင်မပေါ်) ပဲ run မယ်
    HEADLESS_BROWSER = True
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    # --- ⚙️ Server Config ---
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    TIMEZONE = pytz.timezone('Asia/Yangon')

# Folder တွေ မရှိရင် အလိုအလျောက် ဆောက်ပေးမယ့် code
os.makedirs("memory", exist_ok=True)