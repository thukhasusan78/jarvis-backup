import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config import Config

# Core Agent ကို လှမ်းခေါ်မယ်
from core.agent import JarvisAgent
# Formatter ကို သုံးမယ်
from interfaces.formatter import format_response

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("TELEGRAM_INTERFACE")

# Agent ကို Global Variable အနေနဲ့ ကြေညာထားမယ် (Bot စ run မှ အသက်သွင်းမယ်)
agent = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /start"""
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"မင်္ဂလာပါ {user_name} ခင်ဗျာ။ ကျွန်တော် Jarvis ပါ။\nဘာကူညီပေးရမလဲ?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /help"""
    help_text = """
    🛠 **Jarvis Capabilities:**
    1. Chat & Coding Help (Gemini 2.0)
    2. Web Search (Real-time)
    3. Linux VPS Control (Shell)
    4. Memory & Learning
    
    Just type what you want!
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ဆီက စာဝင်လာတိုင်း ဒီ Function က အလုပ်လုပ်မယ်"""
    user_id = update.effective_user.id
    user_text = update.message.text

    # 1. Security Check (မင်း ID မဟုတ်ရင် အလုပ်မလုပ်ဘူး - ပိုက်ဆံကုန်သက်သာအောင်)
    if Config.ALLOWED_USER_ID and user_id != Config.ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Access Denied: You are not my master.")
        return

    # 2. Typing Indicator (Jarvis စဉ်းစားနေကြောင်း ပြမယ်)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 3. Agent ကို အလုပ်ခိုင်းမယ်
    try:
        global agent
        if agent is None:
            agent = JarvisAgent() # လိုအပ်မှ Agent ကို နှိုးမယ်
            
        # Agent ဆီက အဖြေတောင်းမယ်
        response = await agent.chat(user_text, user_id=user_id)
        
        # 4. အဖြေကို Format ချပြီး ပြန်ပို့မယ်
        formatted_reply = format_response(response)
        await update.message.reply_text(formatted_reply)

    except Exception as e:
        logger.error(f"Telegram Error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def run_telegram_bot():
    """Main.py ကနေ လှမ်းခေါ်မယ့် Function"""
    if not Config.TELEGRAM_TOKEN:
        logger.error("❌ Telegram Token missing!")
        return

    logger.info("🤖 Starting Telegram Bot...")
    
    # Application Builder (Latest python-telegram-bot syntax)
    application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Bot ကို Run မယ် (Polling Mode)
    # Note:Main.py ကနေ Async Task အနေနဲ့ run မှာမို့လို့ ဒီမှာ return application လုပ်ပြီး 
    # run_polling() ကို main.py ထဲမှာ control လုပ်တာ ပိုကောင်းပေမဲ့
    # ရိုးရှင်းအောင် ဒီမှာပဲ initialize လုပ်ပြီး run_polling() ကို main process အနေနဲ့ run ခိုင်းလိုက်မယ်။
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Bot run နေသမျှ ကာလပတ်လုံး ဒီ loop ထဲမှာ နေမယ်
    # Stop signal မလာမချင်းပေါ့
    while True:
        await asyncio.sleep(3600) # Keep alive