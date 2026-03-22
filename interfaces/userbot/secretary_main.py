import os
import time
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.handlers import MessageHandler, RawUpdateHandler # 👈 THE FIX: RawUpdateHandler ထည့်သွင်းခြင်း
from pyrogram.raw.types import (
    UpdateNewMessage, MessageService, MessageActionPhoneCall, 
    PhoneCallDiscardReasonMissed, PeerUser
)
from interfaces.userbot.secretary_brain import SecretaryBrain
from memory.sql_storage import sql_storage

logger = logging.getLogger("SECRETARY_MAIN")

try:
    API_ID = int(os.getenv("API_ID", 0))
    VIP_CHAT_ID = int(os.getenv("VIP_CHAT_ID", 0)) 
except ValueError:
    API_ID = 0
    VIP_CHAT_ID = 0

API_HASH = os.getenv("API_HASH", "")

human_active_chats = {}
SILENCE_TIMEOUT = 600

brain = SecretaryBrain()
app = None 

async def track_human_activity(client, message):
    """ဆရာ ကိုယ်တိုင် စာဝင်ရိုက်လိုက်လျှင် မှတ်ထားမည်"""
    chat_id = message.chat.id
    human_active_chats[chat_id] = time.time()
    logger.info(f"👨‍💼 Human (Sir) replied to {chat_id}. Pausing Secretary for 10 mins.")

async def process_secretary_reply(client, chat_id, user_name, user_text, is_bot=False):
    """(Shared Logic) စာဝင်လာလျှင်ဖြစ်စေ၊ Missed Call ဝင်လျှင်ဖြစ်စေ အလုပ်လုပ်မည့် Core Function"""
    if is_bot:
        logger.info(f"🤖 Muted: Ignoring message from BOT ({user_name}) to prevent AI Loop.")
        return

    last_active = human_active_chats.get(chat_id, 0)
    if time.time() - last_active < SILENCE_TIMEOUT:
        logger.info(f"🤫 Muted: Ignoring {user_name} because Sir replied recently.")
        return 

    logger.info(f"👩‍💼 Secretary taking over DM from {user_name}...")
    await client.send_chat_action(chat_id, ChatAction.TYPING)

    if chat_id == VIP_CHAT_ID:
        user_text = f"[SYSTEM NOTE: VIP - GIRLFRIEND] {user_text}"

    # Chat History (၁၀ ကြောင်း) ဆွဲထုတ်ခြင်း
    real_history = []
    async for msg in client.get_chat_history(chat_id, limit=10):
        if getattr(msg, "service", False): continue # Service logs များကျော်မည်
        sender = "Sir" if msg.from_user and msg.from_user.is_self else user_name
        text_content = msg.text or msg.caption or "[Media/Sticker/Voice]"
        if text_content:
            real_history.append(f"{sender}: {text_content}")
    
    real_history.reverse()
    formatted_history = "\n".join(real_history)

    # AI Brain သို့ ပို့ခြင်း
    reply_text = await brain.reply(user_name, user_text, formatted_history)

    if reply_text:
        await client.send_message(chat_id, reply_text)
        await asyncio.to_thread(sql_storage.add_message, chat_id, "user", user_text)
        await asyncio.to_thread(sql_storage.add_message, chat_id, "secretary", reply_text)
        logger.info(f"✅ Secretary successfully replied to {user_name}")

async def handle_incoming_messages(client, message):
    """သာမန် စာဝင်လာလျှင် ဖမ်းမည့် Handler"""
    try:
        if getattr(message, "service", False): return # Service များကို RawUpdate ကသာ ရှင်းမည်
            
        chat_id = message.chat.id
        user_name = message.from_user.first_name if message.from_user else "Guest"
        user_text = message.text or "[Media/Sticker/Voice Attached]"
        is_bot = message.from_user.is_bot if message.from_user else False

        logger.info(f"📩 DEBUG: Message received from {user_name} (ID: {chat_id})")
        await process_secretary_reply(client, chat_id, user_name, user_text, is_bot)

    except Exception as e:
        logger.error(f"❌ Secretary Error handling text message: {e}")

async def handle_raw_updates(client, update, users, chats):
    """🛑 THE FIX: Ringing အချိန်ကို ကျော်ပြီး၊ တကယ် Missed Call ဖြစ်သွားမှသာ ဖမ်းမည်"""
    try:
        if isinstance(update, UpdateNewMessage):
            msg = update.message
            if isinstance(msg, MessageService) and isinstance(msg.action, MessageActionPhoneCall):
                reason = getattr(msg.action, "reason", None)
                
                # duration == 0 ကို ဖြုတ်လိုက်ပါပြီ။ တကယ် ဖုန်းချ/လွတ်သွားမှသာ အလုပ်လုပ်ပါမည်။
                if isinstance(reason, PhoneCallDiscardReasonMissed):
                    if isinstance(msg.peer_id, PeerUser):
                        chat_id = msg.peer_id.user_id
                        if getattr(msg, "out", False) is False: # ဝင်လာသော ဖုန်းဖြစ်လျှင်
                            user = users.get(chat_id)
                            user_name = user.first_name if user else "Guest"
                            logger.info(f"📞 MISSED CALL confirmed from {user_name}. Triggering Secretary...")
                            await process_secretary_reply(client, chat_id, user_name, "[Missed Call / ဖုန်းမကိုင်လိုက်ပါ]", is_bot=False)
    except Exception as e:
        pass

async def start_secretary():
    global app
    if not API_ID or not API_HASH:
        logger.warning("⚠️ API_ID missing. Userbot will not start.")
        return
        
    logger.info("👩‍💼 Starting AI Secretary with Raw MTProto Call Detector...")
    try:
        app = Client("jarvis_secretary", api_id=API_ID, api_hash=API_HASH, workdir="memory")
        
        # Handlers များကို စနစ်တကျ ချိတ်ဆက်ခြင်း
        app.add_handler(MessageHandler(track_human_activity, filters.me & filters.private))
        app.add_handler(MessageHandler(handle_incoming_messages, filters.incoming & filters.private))
        app.add_handler(RawUpdateHandler(handle_raw_updates)) # 👈 Raw JSON ခွဲမည့် Handler အသစ်

        await app.start()
        logger.info("✅ Secretary ONLINE.")
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"❌ Failed to start Secretary: {e}")

if __name__ == "__main__":
    app_manual = Client("jarvis_secretary", api_id=API_ID, api_hash=API_HASH, workdir="memory")
    app_manual.run()