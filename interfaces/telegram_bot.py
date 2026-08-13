import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config import Config

# Formatter နှင့် သီးသန့်ခွဲထုတ်ထားသော Chat Handler ကို လှမ်းခေါ်မည်
from interfaces.formatter import format_response
from memory.memory_controller import memory_controller
from core.chat_handler import process_user_message
import os
import uuid
from perception.media_receiver import process_incoming_image

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("TELEGRAM_INTERFACE")

TELEGRAM_MSG_LIMIT = 4096

async def send_dynamic_response(bot, chat_id: int, text: str):
    """
    📏 Dynamic Telegram Response Strategy (R4):
    - Content သည် Telegram Limit (4096) အတွင်းဆိုရင် → Text အဖြစ် တိုက်ရိုက်ပို့မည်။
    - Limit ကျော်သွားရင် → ဖိုင်အဖြစ် (.md) အလိုအလျောက် Format လုပ်ပြီး Attachment ပို့မည်။
    """
    if len(text) <= TELEGRAM_MSG_LIMIT:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        return
    # Limit ကျော်နေလျှင် ဖိုင်အဖြစ်ပို့မည်
    import io
    file_bytes = io.BytesIO(text.encode("utf-8"))
    file_bytes.name = "jarvis_response.md"
    await bot.send_document(
        chat_id=chat_id,
        document=file_bytes,
        caption="📄 အဖြေရှည်လွားသဖြင့် ဖိုင်အဖြစ် ပို့ပေးလိုက်ပါသည် ဆရာ။"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"မင်္ဂလာပါ {user_name} ခင်ဗျာ။ ကျွန်တော် Jarvis ပါ။\nဘာကူညီပေးရမလဲ?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "🛠 **Jarvis Capabilities:**\n1. Chat & Coding\n2. Web Search\n3. OS Control\nJust type what you want!"
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Security Check
    if Config.ALLOWED_USER_ID and user_id != Config.ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access Denied.")
        return

    # User ဆီက ဝင်လာတာ စာလား? ပုံလား? ခွဲခြားမည်
    user_text = ""
    
    if update.message.photo:
        # 📸 ပုံပို့လိုက်လျှင်
        photo_file = await update.message.photo[-1].get_file()
        os.makedirs("workspace/temp_media", exist_ok=True)
        file_path = os.path.join("workspace", "temp_media", f"img_{update.message.message_id}.jpg")
        
        await photo_file.download_to_drive(file_path)
        caption = update.message.caption or ""
        
        # 🚀 Media Receiver ဆီသို့ ပို့ပြီး Context ပြောင်းမည် (Bottleneck မဖြစ်ပါ)
        user_text = await process_incoming_image(file_path, caption)
        
    elif update.message.text:
        # ✍️ ရိုးရိုး စာပို့လိုက်လျှင်
        user_text = update.message.text
        
        # Reset Command
        if user_text.lower() == "/reset" or user_text == "မေ့လိုက်တော့":
            msg = memory_controller.clear_chat(user_id)
            await update.message.reply_text(f"🧹 {msg}")
            return
    else:
        # Voice (သို့) အခြားအရာများ (လောလောဆယ် ကျော်ထားမည်)
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Task ID အသစ်တစ်ခု အလိုလို ဖန်တီးမည်
    task_id = f"task_{uuid.uuid4().hex[:6]}"

    # Status Update Callback (Task ID လေးပါ တွဲပြပေးမည့်စနစ်)
    status_msg = [None]
    async def send_status_update(msg):
        try:
            display_text = f"<i>{msg}</i>"
            if status_msg[0] is None:
                status_msg[0] = await context.bot.send_message(chat_id=chat_id, text=display_text, parse_mode="HTML")
            else:
                await status_msg[0].edit_text(text=display_text, parse_mode="HTML")
        except Exception:
            pass

    # --- 🚀 FIRE AND FORGET (BACKGROUND TASK) ---
    async def process_task_in_background():
        try:
            # Task ID ကို Chat Handler ဆီ လှမ်းပို့ပေးလိုက်မည်
            response = await process_user_message(user_id, user_text, send_status_update, task_id)

            if status_msg[0]:
                try:
                    await status_msg[0].delete()
                except Exception:
                    pass
            
            # အလုပ်အားလုံးပြီးသွားမှ ဆရာ့ဆီကို Task ID နဲ့တကွ Report အပြီးသတ် လာတင်မည်
            # 📏 R4: Limit အလိုက် Text (သို့) File Attachment အဖြစ် Dynamic ပို့မည်
            formatted_reply = format_response(response)
            await send_dynamic_response(context.bot, chat_id, f"{formatted_reply}")

            # 🧹 Storage မပြည့်အောင် Task ပြီးသွားလျှင် MD ဖိုင်ကို အလိုအလျောက် ရှင်းလင်းမည် (ယာယီပိတ်ထားသည်)
            task_file = os.path.join("workspace", "tasks", "pending", f"{task_id}.md")
            if os.path.exists(task_file):
                try:
                    os.remove(task_file)
                    logger.info(f"🧹 Auto-Cleaned Task File: {task_id}.md")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Task Error: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error in {task_id}: {str(e)}")

    asyncio.create_task(process_task_in_background())

async def run_telegram_bot():
    if not Config.TELEGRAM_TOKEN:
        logger.error("❌ Telegram Token missing!")
        return

    logger.info("🤖 Starting Telegram Bot...")
    application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)