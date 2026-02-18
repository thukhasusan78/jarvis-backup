import uvicorn
import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.scheduler import jarvis_scheduler

# Config နဲ့ Telegram Interface ကို လှမ်းခေါ်မယ်
from config import Config
from interfaces.telegram_bot import run_telegram_bot

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_MAIN")

scheduler = jarvis_scheduler

# --- 🚀 LIFESPAN MANAGER ---
# Server စဖွင့်တာနဲ့ Telegram Bot ကိုပါ တွဲဖွင့်ပေးမယ့် စနစ်
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup Event
    logger.info(f"🔥 System Ignited: {Config.BOT_NAME} v{Config.VERSION}")
    logger.info("📡 Connecting to Neural Network (Gemini 3)...")

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    scheduler.start()
    
    # Telegram Bot ကို Background Task အနေနဲ့ Run မယ်
    # (FastAPI Server နဲ့ ပြိုင်တူ အလုပ်လုပ်စေချင်လို့)
    asyncio.create_task(run_telegram_bot())
    
    yield # Server run နေသမျှ ကာလပတ်လုံး ဒီအောက်က code မ run ဘူး
    
    # 2. Shutdown Event (Ctrl+C နှိပ်ရင်)
    scheduler.shutdown()
    logger.info("🛑 System Shutdown Initiated...")
    logger.info("💤 Jarvis is going to sleep.")

# --- 🌐 FASTAPI APP ---
app = FastAPI(
    title="Jarvis AI Agent API",
    version=Config.VERSION,
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Health Check Endpoint"""
    return {
        "status": "online",
        "agent": Config.BOT_NAME, 
        "mode": "Money Maker Build",
        "tools_status": "Active"
    }

# --- 🔥 ENTRY POINT ---
if __name__ == "__main__":
    # Server ကို Start လုပ်မယ်
    uvicorn.run(
        "main:app", 
        host=Config.HOST, 
        port=Config.PORT
    )