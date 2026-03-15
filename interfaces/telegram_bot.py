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
from perception.media_receiver import process_incoming_image

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("TELEGRAM_INTERFACE")

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
    
    # Status Update Callback (မူလအတိုင်း)
    status_msg = [None]
    async def send_status_update(msg):
        try:
            if status_msg[0] is None:
                status_msg[0] = await context.bot.send_message(chat_id=chat_id, text=f"⏳ <i>{msg}</i>", parse_mode="HTML")
            else:
                await status_msg[0].edit_text(text=f"⏳ <i>{msg}</i>", parse_mode="HTML")
        except Exception:
            pass

    # --- 🚀 FIRE AND FORGET (BACKGROUND TASK) ---
    async def process_task_in_background():
        try:
            response = await process_user_message(user_id, user_text, send_status_update)

            if status_msg[0]:
                try:
                    await status_msg[0].delete()
                except Exception:
                    pass
            
            formatted_reply = format_response(response)
            await context.bot.send_message(chat_id=chat_id, text=formatted_reply)
        except Exception as e:
            logger.error(f"Task Error: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error: {str(e)}")

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