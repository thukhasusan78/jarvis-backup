import logging
import os
from google import genai
from google.genai import types
from config import Config
from core.registry import tool_registry  # <--- NEW: Tool တွေကို ခေါ်သုံးဖို့ ထည့်လိုက်ပါပြီ

logger = logging.getLogger("SECRETARY_BRAIN")

class SecretaryBrain:
    def __init__(self):
        self.api_key = Config.get_next_api_key()
        self.client = genai.Client(api_key=self.api_key)
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

    async def reply(self, user_name: str, text: str, chat_history_text: str) -> str:
        """Async Background Delegation ပါဝင်သော Chat System"""
        try:
            full_prompt = f"Chat History:\n{chat_history_text}\n\nUser ({user_name}): {text}"
            
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7,
                    tools=self.tools_config  # <--- NEW: AI ကို Tool သုံးခွင့် ပေးလိုက်ပါပြီ
                )
            )
            
            # --- NEW: AI က TOOL သုံးခဲ့လျှင် ဖမ်းယူပြီး ASYNC ဖြင့် ခိုင်းစေခြင်း ---
            if response.function_calls:
                for fc in response.function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}
                    logger.info(f"⚙️ Secretary triggering tool: {tool_name} with args: {tool_args}")
                    
                    # နောက်ကွယ်ကနေ Manager ဆီ Task ကို Async နဲ့ ချက်ချင်း ပစ်လွှဲလိုက်မည်
                    await tool_registry.execute_tool(tool_name, **tool_args)
                    
                    # Tool သုံးလိုက်ရင် AI က Customer ဆီ စာပြန်ဖို့ မေ့သွားတတ်လို့ ပုံသေ ပြန်ပေးမည်
                    if not response.text:
                        return "ဟုတ်ကဲ့.. ပြေစာလေး ရပါပြီခင်ဗျာ။ ခဏလေး စောင့်ပေးပါနော်၊ ငွေဝင်တာ စစ်ဆေးပြီးတာနဲ့ VPN Key ချက်ချင်း ပို့ပေးပါ့မယ်ဗျ။"

            return response.text if response.text else "..."
        except Exception as e:
            logger.error(f"Secretary Brain Error: {e}")
            return "ခေတ္တစောင့်ဆိုင်းပေးပါ။ System အနည်းငယ် အခက်အခဲရှိနေပါသည်။"