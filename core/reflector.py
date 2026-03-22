import logging
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger("JARVIS_REFLECTOR")

class JarvisReflector:
    def __init__(self):
        """
        The 'Slow Brain' Debugger.
        Uses a Thinking Model to fix code or command errors.
        """
        self.model = Config.SMART_MODEL_NAME
        self.api_key = Config.get_next_api_key() # Key Rotation သုံးမယ်
        self.client = genai.Client(api_key=self.api_key)

    def reflect_and_fix(self, task: str, failed_command: str, error_log: str) -> str:
        """
        Analyze the error and propose a FIXED command.
        """
        logger.info("🧠 Reflector activated... Switching to Slow Brain.")

        prompt = f"""
        ROLE: You are an Expert Linux SysAdmin and Python Debugger.
        TASK: The user's AI Agent tried to execute a command but FAILED.
        
        --- CONTEXT ---
        USER INTENT: "{task}"
        FAILED COMMAND: `{failed_command}`
        ERROR LOGS:
        {error_log}
        
        --- YOUR GOAL ---
        1. Analyze WHY it failed (Permissions? Typo? Interaction required? Missing tool?).
        2. Provide ONLY the corrected Linux command (or a sequence of commands) to fix it.
        3. If it was a Timeout (waiting for input), use `yes | command` or appropriate flags (like `-y`).
        4. If the error is unfixable via command, explain shortly why.
        
        --- OUTPUT FORMAT ---
        Return ONLY the raw command string. No markdown, no explanation.
        Example: `pip install --upgrade pip`
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2, # တိကျရမယ်၊ လျှောက်မရွှီးရဘူး
                )
            )
            
            fixed_command = response.text.strip().replace("`", "")
            logger.info(f"💡 Reflector proposed fix: {fixed_command}")
            return fixed_command

        except Exception as e:
            logger.error(f"Reflector crashed: {e}")
            return None