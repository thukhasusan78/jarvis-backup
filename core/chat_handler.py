import logging
from core.agent import JarvisAgent
from memory.memory_controller import memory_controller

logger = logging.getLogger("CHAT_HANDLER")
agent = None

async def process_user_message(user_id: int, user_text: str, status_callback=None) -> str:
    """Telegram ကလာတဲ့ စာကို AI ဆီပို့ပြီး အဖြေပြန်ထုတ်ပေးမယ့် Main Logic"""
    global agent
    if agent is None:
        agent = JarvisAgent()

    try:
        # 1. Profile (Long-term) + History (Short-term) ကို ဆွဲထုတ်မယ်
        profile_data = memory_controller.get_all_user_facts(user_id)
        short_term_history = memory_controller.get_recent_chat(user_id, limit=10)
        full_context = f"{profile_data}\n\n--- CHAT HISTORY ---\n"

        # 2. Agent ကို မေးမယ်
        response = await agent.chat(
            user_input=user_text, 
            user_id=user_id, 
            chat_history=short_term_history, 
            context_memory=full_context,
            send_status=status_callback
        )

        # 3. Memory ထဲ ပြန်သိမ်းမယ်
        memory_controller.add_chat_message(user_id, "user", user_text)
        memory_controller.add_chat_message(user_id, "model", response)

        return response
        
    except Exception as e:
        logger.error(f"Chat Handler Error: {e}")
        return f"System Error: {str(e)}"