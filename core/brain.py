import os
import time
import logging
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
        Jarvis Brain Initialization
        """
        # 👈 FIX: Sysadmin ကို Coding သေချာရေးနိုင်ရန် Smart Model (Slow Brain) ချိတ်ပေးမည်
        if role == "sysadmin":
            self.model_name = Config.SMART_MODEL_NAME
        else:
            self.model_name = Config.MODEL_NAME
            
        self.role = role
        # system.md ဖိုင်ထဲကနေ Personality ကို လှမ်းဖတ်မယ်
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'system.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_instruction = f.read()
        
        # Registry ကနေ Role နဲ့ ကိုက်ညီတာကိုပဲ အလိုလို ခွဲယူမယ်
        self.tools_config = [
            types.Tool(
                function_declarations=tool_registry.get_declarations_for_role(self.role)
            )
        ]

    def _get_client(self):
        """Round-Robin Key Rotation: Get a client with the next available key"""
        api_key = Config.get_next_api_key()
        logger.info(f"Using API Key ending in: ...{api_key[-4:]}")
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