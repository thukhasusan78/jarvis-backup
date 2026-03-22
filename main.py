import os
import uvicorn
import asyncio
import logging
# WebSocket ဆိုင်ရာ Library များကို ပေါင်းထည့်ခြင်း
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect 
from interfaces.voice.stream_engine import router as voice_router
from contextlib import asynccontextmanager
from core.scheduler import jarvis_scheduler

from config import Config
from interfaces.telegram_bot import run_telegram_bot
from core.orchestrator import start_orchestrator
from interfaces.userbot.secretary_main import start_secretary

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_MAIN")

scheduler = jarvis_scheduler

# --- 🚀 LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🔥 System Ignited: {Config.BOT_NAME} v{Config.VERSION}")
    logger.info("📡 Connecting to Neural Network (Gemini 3)...")

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    scheduler.start()
    
    asyncio.create_task(run_telegram_bot())
    asyncio.create_task(start_orchestrator())
    asyncio.create_task(start_secretary())
    
    yield 
    
    scheduler.shutdown()
    logger.info("🛑 System Shutdown Initiated...")
    logger.info("💤 Jarvis is going to sleep.")

# --- 🌐 FASTAPI APP ---
app = FastAPI(
    title="Jarvis AI Agent API",
    version=Config.VERSION,
    lifespan=lifespan
)

# 🎙️ Voice Streaming Engine သစ်ကို ချိတ်ဆက်ခြင်း
app.include_router(voice_router)

# 👈 Web UI အတွက် Folder များကို Server တွင် ချိတ်ဆက်ခြင်း
web_dir = os.path.join("interfaces", "web")
os.makedirs(os.path.join(web_dir, "static"), exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")

@app.get("/")
async def root():
    """Main Web Interface ကို ဖွင့်ပေးမည့် Endpoint"""
    return FileResponse(os.path.join(web_dir, "index.html"))



# --- 🔥 ENTRY POINT ---
if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=Config.HOST, 
        port=Config.PORT
    )