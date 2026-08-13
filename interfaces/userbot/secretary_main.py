import os
import logging
import asyncio
from pyrogram import Client
from config import Config
from interfaces.customer_messaging import customer_messaging

logger = logging.getLogger("SECRETARY_MAIN")

try:
    API_ID = int(os.getenv("API_ID", 0))
except ValueError:
    API_ID = 0

API_HASH = os.getenv("API_HASH", "")

app = None 

async def start_secretary():
    global app
    if not API_ID or not API_HASH:
        logger.warning("⚠️ API_ID missing. Userbot will not start.")
        return
        
    logger.info("👩‍💼 Starting Unified Userbot Session (Secretary + Movie Radar)...")
    try:
        # 🌟 plugins=dict(...) ဖြင့် Smart Plugin Architecture ကို ဖွင့်လိုက်ပါပြီ
        # "interfaces.userbot.plugins" Folder ထဲရှိသမျှ Pyrogram code တွေကို အလိုလို Run ပေးပါလိမ့်မယ်။
        app = Client(
            "jarvis_secretary", 
            api_id=API_ID, 
            api_hash=API_HASH, 
            workdir="memory",
            plugins=dict(root="interfaces.userbot.plugins") 
        )

        await app.start()
        logger.info("✅ Userbot Master Session ONLINE. (Plugins Loaded successfully)")

        if Config.VIP_CHANNEL_ID:
            try:
                chat = await customer_messaging.resolve_chat(
                    Config.VIP_CHANNEL_ID
                )
                logger.info(
                    "✅ VIP channel resolved by userbot: %s (%s)",
                    getattr(chat, "title", "unknown"),
                    getattr(chat, "id", Config.VIP_CHANNEL_ID),
                )
            except Exception as exc:
                logger.error("❌ VIP channel preflight failed: %s", exc)
        
        # (မှတ်ချက် - Movie Queue Worker ကို နောက်တစ်ဆင့် p_movie_radar.py ရေးပြီးရင် ဒီနေရာမှာ လာတပ်ပါမယ်)

        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error(f"❌ Failed to start Userbot Session: {e}")

if __name__ == "__main__":
    app_manual = Client(
        "jarvis_secretary", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        workdir="memory",
        plugins=dict(root="interfaces.userbot.plugins")
    )
    app_manual.run()