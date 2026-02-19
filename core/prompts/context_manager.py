import datetime
import logging
from config import Config
from memory.db_manager import db_manager

logger = logging.getLogger("JARVIS_CONTEXT")

class ContextManager:
    @staticmethod
    def get_current_context() -> str:
        """အချိန်နှင့် User ရဲ့ မှတ်ဉာဏ်တွေကို စုစည်းပေးခြင်း"""
        
        # 1. လက်ရှိ မြန်မာစံတော်ချိန်ကို ယူမယ်
        current_time = datetime.datetime.now(Config.TIMEZONE)
        time_str = current_time.strftime("%Y-%m-%d %I:%M %p (%A)")
        
        # 2. Database (Long-term Memory) ထဲက User Profile ကို သွားဆွဲထုတ်မယ် (ဒီနေရာကို ပြင်ထားပါတယ်)
        profile_str = "- No specific user facts saved yet."
        try:
            # db_manager ထဲက get_user_profile ကို မှန်ကန်စွာ ခေါ်ယူခြင်း
            fetched_profile = db_manager.get_user_profile(Config.ALLOWED_USER_ID)
            if fetched_profile:
                profile_str = fetched_profile
        except Exception as e:
            logger.error(f"Error loading user profile: {e}")

        # 3. Jarvis နားလည်မယ့် Context စာသားအဖြစ် ပြောင်းမယ်
        context = f"""
[SYSTEM CONTEXT - DO NOT IGNORE]
🕒 Current Time: {time_str}
📍 Timezone: Asia/Yangon (MMT)

{profile_str}
"""
        return context.strip()

# တခြားနေရာကနေ အလွယ်တကူ လှမ်းခေါ်လို့ရအောင် instance ဆောက်ပေးထားမယ်
context_manager = ContextManager()