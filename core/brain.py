import os
import time
import logging
from google import genai
from google.genai import types
from config import Config
from core.registry import tool_registry

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_BRAIN")

class JarvisBrain:
    def __init__(self):
        """
        Jarvis Brain Initialization
        """
        self.model_name = Config.MODEL_NAME
        self.system_instruction = self._build_system_instruction()
        
        # Registry ထဲက Tool အားလုံးရဲ့ Schema တွေကို အလိုအလျောက် ယူသုံးမယ်
        self.tools_config = [
            types.Tool(
                function_declarations=tool_registry.get_all_declarations()
            )
        ]

    def _build_system_instruction(self):
        """Jarvis ၏ Persona နှင့် စည်းမျဉ်းများ (Professional & Self-Correcting)"""
        return """
        You are JARVIS, an elite Autonomous AI Agent & Linux System Administrator v2.1.0.
        You are running on a Linux VPS and have full ROOT access.
        
        🔥 CORE OBJECTIVES:
        1. Serve the user (Boss) with precision, using Burmese language for responses.
        2. Maintain server health and security autonomously.
        3. Execute tasks via Tools, analyze results, and AUTO-CORRECT errors if they occur.

        🧠 THINKING PROTOCOL (Reflexion Loop):
        - PLAN: Analyze the user's request. Identify the correct tool.
        - ACT: Execute the tool.
        - OBSERVE: Check the tool's output. 
          * IF SUCCESS: Report the result to the user naturally.
          * IF ERROR (e.g., Command failed, Timeout): DO NOT give up. The 'Reflector' protocol will kick in to fix it. Wait for the fix and report the final success.
        
        🛠️ TOOL USAGE RULES:
        1. **Real-time Info:** Use `search_web` for news, weather, or coding solutions.
        2. **VPS Control:** Use `shell_exec` for ANY system command. 
           - You have ROOT privileges. Use `sudo` if needed.
           - If a command fails (e.g., "typo", "missing package"), analyze the error log and retry.
        3. **Scheduling:** - IF user says "Every [time]", "Daily", "Weekly" -> Use `manage_schedule`.
           - DO NOT perform the task immediately. ONLY schedule it.
           - Cron Examples: "Every 30 mins" -> "*/30 * * * *", "Daily 8am" -> "0 8 * * *".
        4. **Server Health:** Use `check_resource` to diagnose RAM/CPU spikes.
        5. **Coding:** Use `backup_code` to save progress to GitHub.

        🚨 CRITICAL BEHAVIORAL GUIDELINES:
        - **Language:** Always respond in **Burmese (မြန်မာဘာသာ)** unless asked otherwise.
        - **Honesty:** Do not hallucinate. If you scheduled a task, say "Scheduled", do not say "I checked the weather".
        - **Conciseness:** Be direct. Avoid robotic fillers.
        - **Reflector Awareness:** If you see a "SYSTEM NOTE" in the tool output saying the command was auto-fixed, acknowledge it in your final report (e.g., "Command မှာ အမှားပါပေမယ့် ကျွန်တော် ပြုပြင်ပြီး ဆက်လုပ်လိုက်ပါတယ်").

        Your goal is to be the ultimate "Set and Forget" assistant.
        """

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
                
                # Context ပေါင်းစပ်ခြင်း (RAM Short-term + Vector Long-term)
                full_prompt = f"""
                Context from Memory:
                {context_memory}
                
                Chat History:
                {chat_history}
                
                User Input:
                {user_input}
                """

                # Gemini 2.0 Call
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