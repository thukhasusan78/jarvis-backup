import uvicorn
import asyncio
import logging
# WebSocket ဆိုင်ရာ Library များကို ပေါင်းထည့်ခြင်း
from core.live_brain import LiveBrain
from fastapi import FastAPI, WebSocket, WebSocketDisconnect 
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

# 👈 Web UI အတွက် Folder များကို Server တွင် ချိတ်ဆက်ခြင်း
web_dir = os.path.join("interfaces", "web")
os.makedirs(os.path.join(web_dir, "static"), exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")

@app.get("/")
async def root():
    """Health Check Endpoint"""
    return {
        "status": "online",
        "agent": Config.BOT_NAME, 
        "mode": "Voice & Web Integrated Build",
        "tools_status": "Active"
    }

# ==========================================
# 🎙️ JARVIS VOICE WEBSOCKET ENDPOINT (PHASE 2)
# ==========================================
@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    """Browser မှ Raw Audio များကို လက်ခံပြီး Live Brain သို့ လွှဲပေးမည့် Endpoint"""
    await websocket.accept()
    client_ip = websocket.client.host
    logger.info(f"🎤 Voice WebSocket Connected! (Client: {client_ip})")

    # Live Brain အင်ဂျင်ကို အသက်သွင်းခြင်း
    live_brain = LiveBrain(websocket)

    try:
        # Session ကို စတင် Run မည် (သူ့ဘာသာ Auto-Reconnect များ လုပ်ပေးသွားပါမည်)
        await live_brain.run_session()

    except WebSocketDisconnect:
        logger.warning(f"⚠️ User closed the browser or connection dropped. (Client: {client_ip})")
    except Exception as e:
        logger.error(f"❌ Voice Session Exception: {e}")
        try:
            await websocket.close(code=1011, reason="Brain Disconnected")
        except Exception:
            pass
    finally:
        logger.info(f"🔒 Voice session fully closed for {client_ip}")

# --- 🔥 ENTRY POINT ---
if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=Config.HOST, 
        port=Config.PORT
    )