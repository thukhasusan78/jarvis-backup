import logging
import os
import asyncio
from google import genai
from google.genai import types
from config import Config
from core.registry import tool_registry

logger = logging.getLogger("SECRETARY_BRAIN")

class SecretaryBrain:
    def __init__(self):
        # 🌟 ပြင်ဆင်ချက်: Key ကို အသေမမှတ်တော့ဘဲ Request လာမှ လှမ်းခေါ်သုံးမည်
        self.model_name = Config.MODEL_NAME
        
        # --- DYNAMIC PROMPT FINDER ---
        base_prompt_dir = os.path.join(os.getcwd(), 'core', 'prompts')
        self.system_instruction = "You are Jarvis, an AI Secretary." 
        
        for root, dirs, files in os.walk(base_prompt_dir):
            if 'secretary.md' in files:
                prompt_path = os.path.join(root, 'secretary.md')
                try:
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        self.system_instruction = f.read()
                        logger.info(f"✅ SUCCESS: Secretary Prompt ကို အောင်မြင်စွာ ဖတ်ယူနိုင်ပါပြီ။ ({prompt_path})")
                    break 
                except Exception as e:
                    logger.error(f"❌ Error reading prompt: {e}")
        
        # --- NEW: SECRETARY အတွက် TOOL များ တပ်ဆင်ခြင်း ---
        self.tools_config = [
            types.Tool(function_declarations=tool_registry.get_declarations_for_role("secretary"))
        ]

    async def reply(self, chat_id: int, user_name: str, text: str, chat_history_text: str) -> str:
        """Async Background Delegation ပါဝင်သော Chat System"""
        import datetime
        current_time = datetime.datetime.now(Config.TIMEZONE)
        time_str = current_time.strftime("%Y-%m-%d %I:%M %p")
        
        # 🚀 AI ကို Chat ID နှင့် အချိန် သိအောင် သင်ပေးလိုက်ခြင်း
        full_prompt = f"SYSTEM NOTE: The current Customer's Chat ID is {chat_id}. Current Myanmar Time is {time_str}.\n\nChat History:\n{chat_history_text}\n\nUser ({user_name}): {text}"
        
        # 🌟 ပြင်ဆင်ချက်: Main Brain အတိုင်း Key Rotation နှင့် Auto-Retry စနစ် ထည့်သွင်းခြင်း
        max_retries = 5
        attempt = 0

        while attempt < max_retries:
            try:
                # Request တစ်ခေါက်လာတိုင်း Key အသစ်တစ်ချောင်းကို အလှည့်ကျ ဆွဲယူမည်
                api_key = Config.get_next_api_key()
                client = genai.Client(api_key=api_key)
                
                response = await client.aio.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.7,
                        tools=self.tools_config  
                    )
                )
                
                if response.function_calls:
                    for fc in response.function_calls:
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}
                        logger.info(f"⚙️ Secretary triggering tool: {tool_name} with args: {tool_args}")
                        
                        # Tool အလုပ်လုပ်မည်
                        await tool_registry.execute_tool(tool_name, **tool_args)
                        
                        if not response.text:
                            return "ဟုတ်ကဲ့.. အချက်အလက်များကို လက်ခံရရှိပါပြီခင်ဗျာ။ ခဏလေး စောင့်ပေးပါနော်။"

                return response.text if response.text else "..."
                
            except Exception as e:
                logger.error(f"❌ Secretary API Error (Attempt {attempt+1}): {str(e)}")
                # 429 ဆိုသည်မှာ Quota ပြည့်သွားခြင်းဖြစ်သည်။ ချက်ချင်း နောက် Key ကို ပြောင်းမည်။
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning("⚠️ Rate Limit hit in Secretary! Rotating to next API Key...")
                    attempt += 1
                    await asyncio.sleep(1) 
                else:
                    logger.warning("⚠️ Unexpected error in Secretary. Retrying...")
                    attempt += 1
                    await asyncio.sleep(2)

        return "စနစ်ပိုင်းဆိုင်ရာ အခက်အခဲလေးဖြစ်သွားလို့ ဆရာလိုင်းပေါ်ရောက်လာရင် စာပြန်ပေးပါလိမ့်မယ်ဗျ။"