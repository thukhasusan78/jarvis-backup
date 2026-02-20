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

    if not user_id or user_id == 0:
        user_id = Config.ALLOWED_USER_ID
    
    try:
        # 1. Agent ကို အလုပ်ခိုင်းခြင်း
        # (Task တစ်ခု run တိုင်း Agent အသစ်ခေါ်တာက Memory Leak မဖြစ်အောင်ပါ)
        agent = JarvisAgent()
        
        # 🔥 FIX: AI ကို "ဒါ နှိုးစက်မြည်တာ၊ ဆရာ့ကို သွားသတင်းပို့တော့" လို့ အတိအကျ အမိန့်ပေးခြင်း
        system_trigger_prompt = f"""
        [SYSTEM ALERT: SCHEDULED EVENT TRIGGERED]
        TIME HAS COME FOR TASK: "{prompt}"
        
        INSTRUCTION: 
        You are JARVIS. The scheduled time for the above task has arrived. 
        Do NOT ask the user when to schedule this. It is happening NOW.
        - If it's a reminder, notify the Sir immediately (e.g., "Sir, it is time to go to work.").
        - If it's a research/report task, use your tools to get the data first, then present the final report to the Sir.
        """
        response = await agent.chat(system_trigger_prompt, user_id=user_id)
        
        # 2. Telegram ပို့ခြင်း (Log တင်မကတော့ဘူး)
        if Config.TELEGRAM_TOKEN and user_id:
            bot = Bot(token=Config.TELEGRAM_TOKEN)
            await bot.send_message(chat_id=user_id, text=f"**Scheduled Report:**\n\n{response}", parse_mode="Markdown")
            logger.info("✅ Report sent to Telegram.")
        else:
            logger.warning("⚠️ Cannot send to Telegram: Token or User ID missing.")
            
    except Exception as e:
        logger.error(f"❌ Scheduled Task Failed: {e}")