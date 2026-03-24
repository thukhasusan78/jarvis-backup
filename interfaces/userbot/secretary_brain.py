import logging
import os
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger("SECRETARY_BRAIN")

class SecretaryBrain:
    def __init__(self):
        self.api_key = Config.get_next_api_key()
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = Config.MODEL_NAME
        
        prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'secretary.md')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.system_instruction = f.read()
        else:
            self.system_instruction = "You are Jarvis, an AI Secretary."

    async def reply(self, user_name: str, text: str, chat_history_text: str) -> str:
        """Tool တွေ လုံးဝမပါတဲ့ Pure Chat System"""
        try:
            full_prompt = f"Chat History:\n{chat_history_text}\n\nUser ({user_name}): {text}"
            
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Secretary Brain Error: {e}")
            return "ခေတ္တစောင့်ဆိုင်းပေးပါ။ System အနည်းငယ် အခက်အခဲရှိနေပါသည်။"