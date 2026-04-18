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

# --- 💔 VIP Ghosting Protocol Variables ---
vip_message_timestamps = []
VIP_MUTE_UNTIL = 0

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

    # AI Brain သို့ ပို့ခြင်း (chat_id ကိုပါ ထည့်ပေးလိုက်ပါ)
    reply_text = await brain.reply(chat_id, user_name, user_text, formatted_history)

    if reply_text:
        await client.send_message(chat_id, reply_text)
        await asyncio.to_thread(sql_storage.add_message, chat_id, "user", user_text)
        await asyncio.to_thread(sql_storage.add_message, chat_id, "secretary", reply_text)
        logger.info(f"✅ Secretary successfully replied to {user_name}")

async def handle_incoming_messages(client, message):
    """စာနှင့် ပုံများကို ဖမ်းယူမည့် Handler အသစ် (CEO Architecture အတိုင်း)"""
    try:
        if getattr(message, "service", False): return 
        
        chat_id = message.chat.id
        user_name = message.from_user.first_name if message.from_user else "Guest"
        is_bot = message.from_user.is_bot if message.from_user else False

        user_text = ""
        
        if message.photo:
            # 📸 ပုံပို့လိုက်လျှင် (CEO ကဲ့သို့ temp_media တွင် သိမ်းမည်)
            import os
            import time
            from perception.media_receiver import process_incoming_image # <--- NEW: Media Receiver ကို ခေါ်သုံးမည်
            
            os.makedirs("workspace/temp_media", exist_ok=True)
            # ဖိုင်နာမည် မထပ်အောင် time ကိုပါ ထည့်သုံးထားသည်
            file_path = os.path.join("workspace", "temp_media", f"img_{chat_id}_{int(time.time())}.jpg")
            
            logger.info(f"📸 Downloading photo from {user_name}...")
            await message.download(file_name=file_path)
            
            caption = message.caption or message.text or ""
            
            # 🚀 CEO ပုံစံအတိုင်း Media Receiver ဆီသို့ ပို့ပြီး Context ပြောင်းမည်
            user_text = await process_incoming_image(file_path, caption)
            
        elif message.text:
            # ✍️ ရိုးရိုး စာပို့လိုက်လျှင်
            user_text = message.text
            
        # စာရော၊ ပုံရော မပါရင် ပယ်ချမည်
        if not user_text and not message.media:
            logger.info("👻 Ghost Message (Video Call Ended / System Log) detected. Dropping instantly.")
            return

        logger.info(f"📩 DEBUG: Message/Media received from {user_name} (ID: {chat_id})")
        
        # Secretary Brain ဆီသို့ ပို့လွှတ်ခြင်း
        await process_secretary_reply(client, chat_id, user_name, user_text, is_bot)

    except Exception as e:
        logger.error(f"❌ Secretary Error handling message: {e}")

async def handle_raw_updates(client, update, users, chats):
    """🛑 THE ULTIMATE FIX: String-based MTProto Parser (2026 Developer Method)"""
    try:
        # Data အကြမ်းကြီးတစ်ခုလုံးကို String အဖြစ် အတင်းပြောင်းလိုက်မည်
        update_str = str(update)
        
        # 💡 Pyrogram ၏ Parsing အခက်အခဲများကို ကျော်ဖြတ်ရန် စာသားတိုက်ရိုက် ရှာဖွေမည်
        is_missed = "PhoneCallDiscardReasonMissed" in update_str
        is_busy = "PhoneCallDiscardReasonBusy" in update_str

        # ဖုန်းမကိုင်လိုက်ခြင်း (Missed) သို့မဟုတ် ဖုန်းချလိုက်ခြင်း (Busy) အတိအကျဖြစ်လျှင်
        if is_missed or is_busy:
            
            # 💡 ကိုယ်က ခေါ်ပြီး တစ်ဖက်လူ မကိုင်တာမျိုး (Outgoing Missed Call) ကို စစ်ထုတ်မည်
            if "out=True" in update_str.replace(" ", ""):
                return # ကိုယ်ခေါ်တာဆိုရင် Secretary က စာဝင်မပြန်ပါ
                
            caller_id = None
            caller_name = "Guest"
            my_id = getattr(client.me, "id", None) if getattr(client, "me", None) else None
            
            # Raw Update ထဲတွင် အလိုလို ပါလာသော တစ်ဖက်လူ (User) ၏ ID နှင့် နာမည်ကို ဆွဲထုတ်မည်
            if users:
                for uid, user in users.items():
                    if my_id and uid == my_id:
                        continue # ကိုယ့် ID ကို ကျော်မည်
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