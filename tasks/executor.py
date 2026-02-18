import asyncio
import logging
from telegram import Bot
from config import Config
from core.agent import JarvisAgent

logger = logging.getLogger("TASK_EXECUTOR")

async def run_scheduled_task(prompt: str, user_id: int):
    """
    Scheduler ကနေ ခေါ်မယ့် Generic Function ပါ။
    ၁။ Agent ကို အလုပ်ခိုင်းမယ်။
    ၂။ အဖြေကို Telegram ပြန်ပို့မယ်။
    """
    logger.info(f"⏰ Running Scheduled Task: {prompt}")
    
    try:
        # 1. Agent ကို အလုပ်ခိုင်းခြင်း
        # (Task တစ်ခု run တိုင်း Agent အသစ်ခေါ်တာက Memory Leak မဖြစ်အောင်ပါ)
        agent = JarvisAgent()
        response = await agent.chat(prompt, user_id=user_id)
        
        # 2. Telegram ပို့ခြင်း (Log တင်မကတော့ဘူး)
        if Config.TELEGRAM_TOKEN and user_id:
            bot = Bot(token=Config.TELEGRAM_TOKEN)
            await bot.send_message(chat_id=user_id, text=f"⏰ **Scheduled Report:**\n\n{response}", parse_mode="Markdown")
            logger.info("✅ Report sent to Telegram.")
        else:
            logger.warning("⚠️ Cannot send to Telegram: Token or User ID missing.")
            
    except Exception as e:
        logger.error(f"❌ Scheduled Task Failed: {e}")