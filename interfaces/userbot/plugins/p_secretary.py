import os
import time
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from interfaces.userbot.secretary_brain import SecretaryBrain
from memory.sql_storage import sql_storage
from memory.memory_extractor import extract_business_facts_from_admin_reply

logger = logging.getLogger("P_SECRETARY")

try:
    VIP_CHAT_ID = int(os.getenv("VIP_CHAT_ID", 0)) 
except ValueError:
    VIP_CHAT_ID = 0

human_active_chats = {}
SILENCE_TIMEOUT = 600

# --- 📸 Last Uploaded Image Tracker (in-memory cache + SQL persistence) ---
last_image_uploads = {}
IMAGE_VALIDITY = 86400  # ၂၄ နာရီ

# --- 💔 VIP Ghosting Protocol Variables ---
vip_message_timestamps = []
VIP_MUTE_UNTIL = 0

brain = SecretaryBrain()


def _load_vip_mute():
    global VIP_MUTE_UNTIL
    try:
        VIP_MUTE_UNTIL = sql_storage.get_vip_mute_until(VIP_CHAT_ID) if VIP_CHAT_ID else 0.0
    except Exception:
        VIP_MUTE_UNTIL = 0.0


def _persist_vip_mute(until: float):
    global VIP_MUTE_UNTIL
    VIP_MUTE_UNTIL = until
    if VIP_CHAT_ID:
        try:
            sql_storage.set_vip_mute_until(VIP_CHAT_ID, until)
        except Exception as e:
            logger.error(f"Failed to persist VIP mute: {e}")


_load_vip_mute()


@Client.on_message(filters.me & filters.private, group=2)
async def track_human_activity(client, message):
    """ဆရာ ကိုယ်တိုင် စာဝင်ရိုက်လိုက်လျှင် မှတ်ထားမည်"""
    chat_id = message.chat.id
    now = time.time()
    human_active_chats[chat_id] = now
    await asyncio.to_thread(sql_storage.set_human_active, chat_id, now)
    logger.info(f"👨‍💼 Human (Sir) replied to {chat_id}. Pausing Secretary for 10 mins.")
    
    # --- 🛑 THE FIX: Personal Chats & Small Talk Filter ---
    # 1. VIP (Girlfriend/Friends) Chat ဆိုရင် RAG Extraction လုံးဝ မလုပ်ပါ
    if chat_id == VIP_CHAT_ID:
        return

    if message.text:
        text_lower = message.text.lower()
        
        # 2. ဂဏန်းပါမှ (သို့) ဈေးရောင်း/ဝယ် စကားလုံးပါမှသာ AI ကို ဖတ်ခိုင်းမည် (Token ချွေတာခြင်း)
        has_numbers = any(char.isdigit() for char in text_lower)
        biz_keywords = ["စျေး", "ကျပ်", "kpay", "wave", "kbz", "mmk", "price", "stock", "ပို့", "ရက်", "လ", "သိန်း", "ထောင်", "ဘတ်", "sold out"]

        if has_numbers or any(kw in text_lower for kw in biz_keywords):
            try:
                recent_context = ""
                async for msg in client.get_chat_history(chat_id, limit=3):
                    sender = "Sir" if msg.from_user and msg.from_user.is_self else "Customer"
                    txt = msg.text or msg.caption or ""
                    if txt:
                        recent_context = f"{sender}: {txt}\n" + recent_context
                
                asyncio.create_task(
                    extract_business_facts_from_admin_reply(chat_id, message.text, recent_context)
                )
            except Exception as e:
                logger.error(f"⚠️ Admin Reply Extraction Error: {e}")
        else:
            # သာမန် စကားပြောသက်သက်ဖြစ်လျှင် AI သို့ မပို့ဘဲ ကျော်သွားမည်
            logger.info("⏭️ Skipped Extraction: Just casual talk (No business data detected).")

async def process_secretary_reply(client, chat_id, user_name, user_text, is_bot=False):
    """(Shared Logic) စာဝင်လာလျှင်ဖြစ်စေ၊ Missed Call ဝင်လျှင်ဖြစ်စေ အလုပ်လုပ်မည့် Core Function"""
    if is_bot:
        logger.info(f"🤖 Muted: Ignoring message from BOT ({user_name}) to prevent AI Loop.")
        return

    last_active = human_active_chats.get(chat_id)
    if last_active is None:
        last_active = await asyncio.to_thread(sql_storage.get_human_active_until, chat_id)
        if last_active:
            human_active_chats[chat_id] = last_active
    last_active = last_active or 0
    if time.time() - last_active < SILENCE_TIMEOUT:
        logger.info(f"🤫 Muted: Ignoring {user_name} because Sir replied recently.")
        return

    logger.info(f"👩‍💼 Secretary taking over DM from {user_name}...")
    await client.send_chat_action(chat_id, ChatAction.TYPING)

    if chat_id == VIP_CHAT_ID:
        global VIP_MUTE_UNTIL, vip_message_timestamps
        _load_vip_mute()

        # (၁) လက်ရှိအချိန်က Mute လုပ်ထားတဲ့ (၁ နာရီ) အတွင်းမှာဆိုရင် လုံးဝ စာမပြန်ဘဲ ငြိမ်နေမည်
        if time.time() < VIP_MUTE_UNTIL:
            logger.info("🤫 [VIP MUTED] ကောင်မလေး စိတ်ဆိုးနေသဖြင့် Jarvis ဝင်မဖြေဘဲ ငြိမ်နေပါသည်။")
            return

        # (၂) နောက်ဆုံး ၁ မိနစ် (စက္ကန့် ၆၀) အတွင်း ပို့ထားတဲ့ စာတွေရဲ့ အချိန်ကိုပဲ မှတ်ထားမည်
        current_time = time.time()
        vip_ts = await asyncio.to_thread(sql_storage.get_vip_timestamps, VIP_CHAT_ID)
        vip_message_timestamps = list(vip_ts) if vip_ts else vip_message_timestamps
        vip_message_timestamps.append(current_time)
        vip_message_timestamps = [t for t in vip_message_timestamps if current_time - t <= 60]
        await asyncio.to_thread(sql_storage.set_vip_timestamps, VIP_CHAT_ID, vip_message_timestamps)

        # (၃) ၁ မိနစ်အတွင်း စာ ၃ ကြောင်း ပြည့်သွားရင် ၁ နာရီ (၃၆၀၀ စက္ကန့်) Mute ချမည်
        if len(vip_message_timestamps) >= 3:
            _persist_vip_mute(current_time + 3600)
            logger.warning("🚨 [GHOSTING PROTOCOL ACTIVATED] ၁ မိနစ်အတွင်း စာ ၃ ကြောင်း ဆက်တိုက်ဝင်လာသဖြင့် ၁ နာရီတိတိ Mute ချလိုက်ပါပြီ။")
            return

        user_text = f"[SYSTEM NOTE: VIP - GIRLFRIEND] {user_text}"

    # --- 📸 Persist last image path across turns ---
    if "[SYSTEM: User uploaded an image" not in user_text:
        last_img = last_image_uploads.get(chat_id)
        if not last_img:
            persisted = await asyncio.to_thread(sql_storage.get_last_image, chat_id)
            if persisted and persisted[0]:
                last_img = persisted
                last_image_uploads[chat_id] = persisted
        if last_img:
            img_path, img_ts = last_img
            if time.time() - img_ts < IMAGE_VALIDITY:
                user_text += f"\n[SYSTEM NOTE: This customer's most recent uploaded image is still available at File Path: '{img_path}'. Use this path if you need to publish a payment-verification event.]"
            else:
                last_image_uploads.pop(chat_id, None)
                await asyncio.to_thread(sql_storage.clear_last_image, chat_id)

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
            from perception.media_receiver import process_incoming_image

            os.makedirs("workspace/temp_media", exist_ok=True)
            file_path = os.path.join("workspace", "temp_media", f"img_{chat_id}_{int(time.time())}.jpg")
            
            logger.info(f"📸 Downloading photo from {user_name}...")
            await message.download(file_name=file_path)
            caption = message.caption or message.text or ""
            last_image_uploads[chat_id] = (file_path, time.time())
            await asyncio.to_thread(sql_storage.set_last_image, chat_id, file_path, time.time())
            user_text = await process_incoming_image(file_path, caption, chat_id=chat_id)
            
        elif message.text:
            # --- 🧹 /clear Command: Customer ကိုယ်တိုင် Chat History ရှင်းလင်းနိုင်ရန် ---
            if message.text.strip().lower() in ("/clear", "/new", "/restart"):
                logger.info(f"🧹 /clear command received from {user_name} (ID: {chat_id})")
                try:
                    # 1. Telegram ဘက်ခြမ်း Message များ (နောက်ဆုံး ၁၀၀) ကို နှစ်ဘက်စလုံးအတွက် ဖျက်ခြင်း
                    msg_ids = [m.id async for m in client.get_chat_history(chat_id, limit=100)]
                    if msg_ids:
                        await client.delete_messages(chat_id, msg_ids)
                except Exception as e:
                    logger.error(f"⚠️ Failed to delete Telegram messages for {chat_id}: {e}")
                # 2. Jarvis ရဲ့ Internal Memory (SQL), Image Tracker နှင့် Vision Quota ကို ရှင်းလင်းခြင်း
                await asyncio.to_thread(sql_storage.clear_history, chat_id)
                await asyncio.to_thread(sql_storage.set_vision_timestamps, chat_id, [])
                last_image_uploads.pop(chat_id, None)
                await asyncio.to_thread(sql_storage.clear_last_image, chat_id)
                await client.send_message(
                    chat_id,
                    "🧹 စကားပြောခင်း မှတ်တမ်းအားလုံး ရှင်းလင်းပြီးပါပြီ။ အစကနေ ပြန်လည် စတင်နိုင်ပါပြီခင်ဗျာ။"
                )
                return

            user_text = message.text

        # --- 💬 R6: Reply-Quote Context Capture ---
        # Customer က အရင်စာ/ပုံတစ်ခုကို reply (quote) လုပ်ပြီး မေးနေတာဆိုရင် (ဥပမာ "ဒါကစျေးဘယ်လောက်လဲ")
        # ဘယ်ပုံ/ဘယ်စာကို ရည်ညွှန်းတာလဲ ဆိုတာကို Brain သိရအောင် SYSTEM NOTE ထည့်ပေးမည်။
        replied = getattr(message, "reply_to_message", None)
        if replied and user_text:
            quoted = replied.text or replied.caption
            if quoted:
                user_text += (
                    f"\n[SYSTEM: Customer is replying to (quoting) a previous message. "
                    f"Quoted message text/caption: \"{quoted}\" — use this to resolve references "
                    f"like 'ဒါ', 'အဲ့တာ', 'this one'.]"
                )
            elif getattr(replied, "media", None):
                user_text += (
                    "\n[SYSTEM: Customer is replying to (quoting) a previous photo/media message "
                    "that has NO caption, so the exact content is unknown. If the question depends "
                    "on WHICH photo it is, politely ask the customer to clarify instead of guessing.]"
                )

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