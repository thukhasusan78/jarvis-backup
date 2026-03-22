import os
import time
import logging
import asyncio
from google import genai
from google.genai import types
from config import Config
from core.registry import tool_registry
from core.prompts.context_manager import context_manager

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_BRAIN")

class JarvisBrain:
    def __init__(self, role: str = "ceo"):
        """
        Jarvis Brain Initialization with Dynamic Model Routing
        """
        self.role = role
        self.model_name = Config.MODEL_NAME  # Default အနေနဲ့ Normal Model ကို အရင်ပေးထားမယ်
        
        # ၁။ Agent ရဲ့ ကိုယ်ပိုင်ဖိုင် (ဥပမာ content_writer.md) ရှိမရှိ အရင်ရှာမယ်
        role_prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', f'{self.role}.md')
        system_prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'system.md')
        
        # ကိုယ်ပိုင်ဖိုင်ရှိရင် အဲဒါဖတ်မယ်၊ မရှိရင် system.md ကို ဖတ်မယ်
        prompt_path = role_prompt_path if os.path.exists(role_prompt_path) else system_prompt_path
        
        # Orbit သုံးမသုံး ခွဲခြားရန် Flag
        self.use_orbit = False
        
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.system_instruction = f.read()
                
            # 💡 SMART ROUTER LOGIC: (မူလအတိုင်း ထားရှိသည်)
            if "[MODEL: SMART]" in self.system_instruction:
                self.model_name = Config.SMART_MODEL_NAME
                
            # 🚀 ORBIT DYNAMIC LOGIC: ဖိုင်ထဲမှာ [PROVIDER: ORBIT] ပါရင် Claude 4.6 နဲ့ Orbit ကို သုံးမည်
            if "[PROVIDER: ORBIT]" in self.system_instruction:
                self.use_orbit = True
                self.model_name = Config.QA_MODEL_NAME
        else:
            self.system_instruction = "You are a helpful AI assistant."
        
        # Registry ကနေ Role နဲ့ ကိုက်ညီတာကိုပဲ အလိုလို ခွဲယူမယ်
        self.tools_config = [
            types.Tool(
                function_declarations=tool_registry.get_declarations_for_role(self.role)
            )
        ]

    def _get_client(self):
        """Round-Robin Key Rotation or Orbit Gateway"""
        
        # 🔥 ORBIT PROVIDER LOGIC: Agent မှာ [PROVIDER: ORBIT] Tag ပါလာရင် ဒီလမ်းကြောင်းက သွားမယ်
        if getattr(self, "use_orbit", False) and hasattr(Config, "ORBIT_API_KEY") and Config.ORBIT_API_KEY:
            logger.info(f"Using ORBIT API Key for {self.role.upper()} ({self.model_name})")
            return genai.Client(
                api_key=Config.ORBIT_API_KEY, 
                http_options={
                    'base_url': Config.ORBIT_BASE_URL,
                    'api_version': 'v1beta',
                    'headers': {
                        'Authorization': f'Bearer {Config.ORBIT_API_KEY}',
                        'X-API-Key': Config.ORBIT_API_KEY
                    }
                }
            )
            
        # 🌐 NORMAL LOGIC: သာမန် Agent တွေဆိုရင် မူလ .env ထဲက Google Key တွေကို လှည့်သုံးမယ်
        api_key = Config.get_next_api_key()
        logger.info(f"Using Standard API Key ending in: ...{api_key[-4:]}")
        return genai.Client(api_key=api_key)

    def think(self, user_input, chat_history=[], context_memory=""):
        """
        The Main Thinking Process with Automatic Retry & Key Rotation
        """
        max_retries = 5  # Key 5 ခုရှိလို့ ၅ ခါ retry မယ်
        attempt = 0

        while attempt < max_retries:
            try:
                client = self._get_client()
                
                # ပွဲစား (Context Manager) ဆီကနေ အချိန်နဲ့ မှတ်ဉာဏ်တွေကို ယူမယ်
                dynamic_context = context_manager.get_current_context()

                # Context ပေါင်းစပ်ခြင်း
                full_prompt = f"""
                {dynamic_context}
                
                Context from Memory:
                {context_memory}
                
                Chat History:
                {chat_history}
                
                User Input:
                {user_input}
                """

                # Gemini 2.5 Call
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        tools=self.tools_config,
                        temperature=0.7, # Creative but focused
                    )
                )
                
                return response

            except Exception as e:
                logger.error(f"API Error with key attempt {attempt+1}: {e}")
                
                # 429 means Rate Limit - Rotate Key immediately
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning("Rate Limit hit! Rotating to next API Key...")
                    attempt += 1
                    time.sleep(1) # ခဏစောင့်ပြီး နောက် Key ပြောင်း
                else:
                    # တခြား Error ဆိုရင်လည်း Retry မယ် (Network error ဖြစ်နိုင်လို့)
                    logger.warning(f"Unexpected error. Rotating key just in case. Error: {e}")
                    attempt += 1
                    time.sleep(2)

        return "Error: All API Keys failed. Please check your quota or connection."

    async def stream_think(self, user_input, chat_history=[], context_memory=""):
            """
            Voice WebSocket အတွက် အသံချက်ချင်းထုတ်နိုင်ရန် True Streaming ပြုလုပ်ပေးမည့် Function အသစ်
            (Tools များနှင့် Context များကို အပြည့်အဝ အသုံးပြုနိုင်သည်)
            """
            try:
                # 1. Client နှင့် အချက်အလက်များ ပြင်ဆင်ခြင်း
                client = self._get_client()
                dynamic_context = context_manager.get_current_context()
                
                full_prompt = f"""
                {dynamic_context}
                
                Context from Memory:
                {context_memory}
                
                Chat History:
                {chat_history}
                
                User Input:
                {user_input}
                """

                # 2. Config သတ်မှတ်ခြင်း (Tools များ ပါဝင်သည်)
                config = types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=self.tools_config,
                    temperature=0.7,
                )

                # 3. 🤖 Async Stream ဖြင့် Gemini ထံမှ အဖြေကို တောင်းခံခြင်း
                # (မှတ်ချက် - Orbit API က Streaming မရနိုင်သေးပါက Error တက်နိုင်သဖြင့် Normal Model ကိုသာ ဦးစားပေးသုံးသည်)
                model_to_use = self.model_name
                if self.use_orbit:
                    logger.warning("Orbit API might not support True Streaming yet. Falling back to Normal Model.")
                    client = genai.Client(api_key=Config.get_next_api_key())
                    model_to_use = Config.MODEL_NAME

                response_stream = await client.aio.models.generate_content_stream(
                    model=model_to_use,
                    contents=full_prompt,
                    config=config
                )

                # 4. ⚡ ရလာသော အဖြေများကို Yield (အပိုင်းလိုက်) ဖြင့် ပြန်ထုတ်ပေးခြင်း
                async for chunk in response_stream:
                    
                    # --- Tool Call များကို ဖမ်းယူခြင်း ---
                    if chunk.function_calls:
                        for fc in chunk.function_calls:
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}
                            logger.info(f"⚙️ Streaming Brain executing tool: {tool_name}")
                            
                            # Registry မှ Tool ကို အမှန်တကယ် Run မည်
                            tool_result = await tool_registry.execute_tool(tool_name, **tool_args)
                            
                            # Tool အဖြေကို AI ဆီ ပြန်ပို့ပြီး အသံဖြင့် ပြန်ဖြေခိုင်းမည့် အပိုင်းကို 
                            # နောက်ပိုင်းတွင် ထပ်မံ အဆင့်မြှင့်တင်နိုင်ပါသည်။
                            # (လောလောဆယ် Web UI တွင် Hologram ပြရန် JSON သာ ထုတ်ပေးမည်)
                            yield f'{{"type": "hologram_trigger", "action": "render_tool", "data": "{tool_name} executed"}}'
                    
                    # --- ပုံမှန် စာသားများကို ဖမ်းယူခြင်း ---
                    if chunk.text:
                        yield chunk.text

            except Exception as e:
                logger.error(f"❌ Streaming Error: {e}")
                yield "တောင်းပန်ပါတယ် ဆရာ၊ အင်တာနက် ချိတ်ဆက်မှု အဆင်မပြေဖြစ်နေပါတယ်။"        