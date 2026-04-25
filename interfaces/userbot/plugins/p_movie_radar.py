import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.raw.types import UpdateNewChannelMessage
from config import Config
from core.movie_engine import process_and_publish_movie

logger = logging.getLogger("P_MOVIE_RADAR")

# ==========================================
# 🚦 TASK QUEUE SYSTEM (စနစ်မကျပ်စေရန် တန်းစီစနစ်)
# ==========================================
movie_queue = asyncio.Queue()
worker_started = False

async def queue_worker(client):
    """Queue ထဲရောက်လာသမျှကို တစ်ကားပြီးမှ တစ်ကား အေးဆေး တင်ပေးမည့် အလုပ်သမား"""
    logger.info("👷 Movie Queue Worker စတင် အလုပ်လုပ်နေပါပြီ...")
    while True:
        task = await movie_queue.get()
        source_msg = task['message']
        raw_name = task['raw_file_name']
        
        try:
            logger.info(f"⏳ [Queue Processing] '{raw_name}' ကို စတင် ဆောင်ရွက်နေပါပြီ...")
            # 🌟 Refactored Engine ဆီသို့ client ကိုပါ ထည့်ပေးလိုက်ခြင်း
            success = await process_and_publish_movie(client=client, source_message=source_msg, raw_file_name=raw_name)
            
            if success:
                logger.info(f"🎉 '{raw_name}' ပို့စ်တင်ခြင်း အောင်မြင်သွားပါပြီ!")
            else:
                logger.error(f"❌ '{raw_name}' တင်ရာတွင် အခက်အခဲဖြစ်သွားပါသည် (သို့) တင်ပြီးသားဖြစ်နေသည်။")
        except Exception as e:
            logger.error(f"❌ Worker Error: {e}")
        finally:
            movie_queue.task_done()
            logger.info("🧹 နောက်တစ်ကားအတွက် အဆင်သင့်ဖြစ်ပါပြီ...\n")

# ==========================================
# 🤖 THE BRUTE-FORCE RADAR (PLUGIN VERSION)
# ==========================================
@Client.on_raw_update()
async def new_movie_radar(client, update, users, chats):
    global worker_started

    if not worker_started:
        asyncio.create_task(queue_worker(client))
        worker_started = True

    # ၁။ "အထုပ်ဖြည်ပြီး" Channel Message အသစ် ဟုတ်/မဟုတ် အတိအကျ စစ်ဆေးခြင်း
    if not isinstance(update, UpdateNewChannelMessage):
        return

    raw_msg = update.message
    if not hasattr(raw_msg, "peer_id") or not hasattr(raw_msg, "id"):
        return

    # ၂။ Channel ID ကို ပြောင်းလဲခြင်း (-100 တပ်ပေးမှ Pyrogram ID ရပါမည်)
    try:
        chat_id = int(f"-100{raw_msg.peer_id.channel_id}")
    except Exception:
        return

    allowed_ids = [int(x) for x in Config.MONITOR_CHANNELS]

    if chat_id not in allowed_ids:
        return

    # ၃။ ID ရပြီဖြစ်၍ Pyrogram ၏ Message အစစ်ကို တိုက်ရိုက် လှမ်းဆွဲယူခြင်း
    # (ဤသို့လုပ်ခြင်းဖြင့် အောက်ပိုင်းရှိ မူရင်း Feature များ လုံးဝမပျက်တော့ပါ)
    try:
        message = await client.get_messages(chat_id, raw_msg.id)
        if not message or getattr(message, 'empty', True):
            return

        # ၄။ ဇာတ်ကားဖိုင် ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
        if not (message.video or message.document):
            return

    except Exception as e:
        logger.error(f"❌ Radar Message Fetch Error: {e}")
        return

    logger.info(f"🚨 [RADAR TRIGGERED] ပစ်မှတ် Channel (ID: {chat_id}) မှ ဇာတ်ကားဖိုင် ထောက်လှမ်းမိပါပြီ!")

    try:
        media_obj = message.video if message.video else message.document
        raw_file_name = getattr(media_obj, 'file_name', None)
        
        # --- ဇာတ်ကားနာမည် ထုတ်ယူခြင်း (Priority System) ---
        final_movie_name = None

        # ၁။ Caption မှ ယူခြင်း
        if message.caption:
            final_movie_name = message.caption.split('\n')[0][:60]
        
        # ၂။ အပေါ်ပို့စ် (Poster) မှ ယူခြင်း
        if not final_movie_name:
            try:
                prev_msg = await client.get_messages(message.chat.id, message.id - 1)
                target_text = prev_msg.caption if prev_msg.caption else prev_msg.text
                if target_text:
                    final_movie_name = target_text.split('\n')[0][:60]
            except:
                pass

        # ၃။ ဖိုင်နာမည်မှ ယူခြင်း
        if not final_movie_name and raw_file_name:
            if "video" not in raw_file_name.lower() and "document" not in raw_file_name.lower():
                final_movie_name = raw_file_name

        if not final_movie_name:
            final_movie_name = "Unknown Movie"
            
        logger.info(f"🚀 '{final_movie_name}' ကို Waiting List ထဲသို့ ထည့်သွင်းလိုက်ပါပြီ။")

        # Queue ထဲသို့ Client ရော Message ပါ ထည့်လိုက်ခြင်း
        await movie_queue.put({
            "message": message,
            "raw_file_name": final_movie_name
        })

    except Exception as e:
        logger.error(f"❌ Monitor Error: {e}")