import os
import time
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.raw.types import (
    UpdateNewMessage, MessageService, MessageActionPhoneCall, 
    PhoneCallDiscardReasonMissed, PeerUser
)
from interfaces.userbot.secretary_brain import SecretaryBrain
from memory.sql_storage import sql_storage

logger = logging.getLogger("P_SECRETARY")

try:
    VIP_CHAT_ID = int(os.getenv("VIP_CHAT_ID", 0)) 
except ValueError:
    VIP_CHAT_ID = 0

human_active_chats = {}
SILENCE_TIMEOUT = 600

# --- 💔 VIP Ghosting Protocol Variables ---
vip_message_timestamps = []
VIP_MUTE_UNTIL = 0

brain = SecretaryBrain()

@Client.on_message(filters.me & filters.private, group=2)
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
        global VIP_MUTE_UNTIL, vip_message_timestamps
        
        # (၁) လက်ရှိအချိန်က Mute လုပ်ထားတဲ့ (၁ နာရီ) အတွင်းမှာဆိုရင် လုံးဝ စာမပြန်ဘဲ ငြိမ်နေမည်
        if time.time() < VIP_MUTE_UNTIL:
            logger.info("🤫 [VIP MUTED] ကောင်မလေး စိတ်ဆိုးနေသဖြင့် Jarvis ဝင်မဖြေဘဲ ငြိမ်နေပါသည်။")
            return
            
        # (၂) နောက်ဆုံး ၁ မိနစ် (စက္ကန့် ၆၀) အတွင်း ပို့ထားတဲ့ စာတွေရဲ့ အချိန်ကိုပဲ မှတ်ထားမည်
        current_time = time.time()
        vip_message_timestamps.append(current_time)
        vip_message_timestamps = [t for t in vip_message_timestamps if current_time - t <= 60]
        
        # (၃) ၁ မိနစ်အတွင်း စာ ၃ ကြောင်း ပြည့်သွားရင် ၁ နာရီ (၃၆၀၀ စက္ကန့်) Mute ချမည်
        if len(vip_message_timestamps) >= 3:
            VIP_MUTE_UNTIL = current_time + 3600
            logger.warning("🚨 [GHOSTING PROTOCOL ACTIVATED] ၁ မိနစ်အတွင်း စာ ၃ ကြောင်း ဆက်တိုက်ဝင်လာသဖြင့် ၁ နာရီတိတိ Mute ချလိုက်ပါပြီ။")
            return

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
    reply_text = await brain.reply(chat_id, user_name, user_text, formatted_history)

    if reply_text:
        await client.send_message(chat_id, reply_text)
        await asyncio.to_thread(sql_storage.add_message, chat_id, "user", user_text)
        await asyncio.to_thread(sql_storage.add_message, chat_id, "secretary", reply_text)
        logger.info(f"✅ Secretary successfully replied to {user_name}")

@Client.on_message(filters.incoming & filters.private, group=3)
async def handle_incoming_messages(client, message):
    """စာနှင့် ပုံများကို ဖမ်းယူမည့် Handler အသစ် (CEO Architecture အတိုင်း)"""
    try:
        if getattr(message, "service", False): return 
        
        chat_id = message.chat.id
        user_name = message.from_user.first_name if message.from_user else "Guest"
        is_bot = message.from_user.is_bot if message.from_user else False

        user_text = ""
        
        if message.photo:
            import os
            import time
            from perception.media_receiver import process_incoming_image 
            
            os.makedirs("workspace/temp_media", exist_ok=True)
            file_path = os.path.join("workspace", "temp_media", f"img_{chat_id}_{int(time.time())}.jpg")
            
            logger.info(f"📸 Downloading photo from {user_name}...")
            await message.download(file_name=file_path)
            caption = message.caption or message.text or ""
            user_text = await process_incoming_image(file_path, caption)
            
        elif message.text:
            user_text = message.text
            
        if not user_text and not message.media:
            logger.info("👻 Ghost Message (Video Call Ended / System Log) detected. Dropping instantly.")
            return

        logger.info(f"📩 DEBUG: Message/Media received from {user_name} (ID: {chat_id})")
        
        await process_secretary_reply(client, chat_id, user_name, user_text, is_bot)

    except Exception as e:
        logger.error(f"❌ Secretary Error handling message: {e}")

@Client.on_raw_update(group=4)
async def handle_raw_updates(client, update, users, chats):
    """🛑 THE ULTIMATE FIX: String-based MTProto Parser"""
    try:
        update_str = str(update)
        is_missed = "PhoneCallDiscardReasonMissed" in update_str
        is_busy = "PhoneCallDiscardReasonBusy" in update_str

        if is_missed or is_busy:
            if "out=True" in update_str.replace(" ", ""):
                return 
                
            caller_id = None
            caller_name = "Guest"
            my_id = getattr(client.me, "id", None) if getattr(client, "me", None) else None
            
            if users:
                for uid, user in users.items():
                    if my_id and uid == my_id:
                        continue 
                    caller_id = uid
                    caller_name = getattr(user, "first_name", "Guest")
                    break
                    
            if caller_id:
                logger.info(f"📞 MISSED CALL accurately detected from {caller_name}! Triggering Secretary...")
                await process_secretary_reply(
                    client, caller_id, caller_name, 
                    "[Missed Call / ဖုန်းမကိုင်လိုက်ပါ]", 
                    is_bot=False
                )
    except Exception as e:
        logger.error(f"Raw Update Error: {e}")