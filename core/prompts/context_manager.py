import datetime
import logging
from config import Config
from memory.memory_controller import memory_controller

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
            fetched_profile = memory_controller.get_all_user_facts(Config.ALLOWED_USER_ID)
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

🏢 [JARVIS ORGANIZATION CHART & HIERARCHY]
Main AI (CEO) MUST NEVER assign tasks directly to Worker Agents. Always delegate to the respective Managers.

1. 👑 EXECUTIVE TIER (Report Directly to CEO):
   - sysadmin: Server/Terminal Management.
   - researcher / deep_researcher: Web search, news gathering, and deep market research.

2. 💼 BUSINESS TIER (Customer-facing, via Message Broker):
   - secretary: Customer chat, sales (VIP subscriptions, Bluetooth jammers).
   - business_manager: Payment verification, invite links, order receipts.

🔄 [DYNAMIC WORKFLOW & MESSAGE BROKER PROTOCOL]
1. NO DIRECT CALLS: Agents do not call each other directly. When your task is done, you MUST use the `publish_event` tool to send your result to the Message Broker.
2. MANAGERS' DUTY: If you are a Manager, read the task, break it down, and use `publish_event` to queue tasks for your workers.
3. THE FINAL REPORT: Only the CEO receives the final "WORKFLOW_COMPLETED" event. The CEO will then use the `report_to_sir` tool to inform the user.

🛑 [ANTI-HALLUCINATION & LANGUAGE LOCK]
1. ALWAYS think, write, and communicate with the Sir in fluent Burmese (မြန်မာစာ).
2. NEVER FAKE ACTIONS. If a task requires a tool, you MUST actually call that tool. If the tool was not used, DO NOT claim the action was done.
"""
        return context.strip()

# တခြားနေရာကနေ အလွယ်တကူ လှမ်းခေါ်လို့ရအောင် instance ဆောက်ပေးထားမယ်
context_manager = ContextManager()