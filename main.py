import uvicorn
import asyncio
import logging
# WebSocket ဆိုင်ရာ Library များကို ပေါင်းထည့်ခြင်း
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
# 🎙️ JARVIS VOICE WEBSOCKET ENDPOINT (PHASE 1)
# ==========================================
@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    """
    Browser မှ Raw Audio များကို လက်ခံမည့် Endpoint
    Cloudflared Tunnel (jarvis.thukha.online/ws/voice) မှတစ်ဆင့် ဝင်လာပါမည်။
    """
    # 1. Connection ကို လက်ခံခြင်း
    await websocket.accept()
    client_ip = websocket.client.host
    logger.info(f"🎤 Voice WebSocket Connected! (Client: {client_ip})")

    try:
        # Phase 2 တွင် ဤနေရာ၌ Gemini Live API ချိတ်ဆက်မှုကို စတင်ပါမည်။
        
        while True:
            # 2. Browser ထံမှ Audio Bytes များကို အဆက်မပြတ် ဖမ်းယူခြင်း
            # Note: WebUI မှ Audio များကို Float32 သို့မဟုတ် PCM16 format ဖြင့် ပို့ပေးရပါမည်။
            data = await websocket.receive_bytes()
            
            # (Testing) Data ဝင်လာကြောင်း Log ထုတ်ပြခြင်း 
            # အသံဖိုင် ဝင်လာတိုင်း Log တွေ ရှုပ်မနေအောင် Debugging အချိန်မှာပဲ ဖွင့်ထားသင့်ပါတယ်။
            # logger.info(f"📥 Received Audio Chunk: {len(data)} bytes")

            # Phase 2 တွင် ရလာသော data ကို Gemini ဆီ တိုက်ရိုက် Stream လုပ်မည်။
            # ပြီးလျှင် Gemini မှ ပြန်လာသော အသံကို await websocket.send_bytes() ဖြင့် ပြန်ပို့ပါမည်။

    except WebSocketDisconnect:
        # User ဘက်မှ Browser ပိတ်သွားခြင်း သို့မဟုတ် Connection ပြတ်သွားခြင်း
        logger.warning(f"⚠️ Voice WebSocket Disconnected cleanly. (Client: {client_ip})")
        # Phase 2 တွင် ဤနေရာ၌ Gemini Session ကို သေချာ ပြန်ပိတ်ပေးရပါမည်။
        
    except Exception as e:
        # အခြားသော မမျှော်လင့်ထားသည့် Error များ (Network Error စသည်)
        logger.error(f"❌ Voice WebSocket Error: {e}")
        try:
            # Error တက်သွားလျှင် Connection ကို သေချာ ပြန်ပိတ်ခြင်း
            await websocket.close(code=1011, reason="Unexpected Server Error")
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