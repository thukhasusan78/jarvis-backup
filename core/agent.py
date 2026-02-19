import logging
import json
import traceback
import asyncio
import uuid
from typing import Dict, Any

# Core Modules
from core.brain import JarvisBrain
from core.reflector import JarvisReflector
from core.registry import tool_registry
from config import Config
from memory.db_manager import db_manager    

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_AGENT")

class JarvisAgent:
    def __init__(self):
        """Jarvis Agent - The Executive Manager"""
        logger.info("🤖 Initializing Jarvis Agent (Professional Build)...")
        
        self.brain = JarvisBrain()
        self.reflector = JarvisReflector()

        logger.info(f"✅ Agent Online: {Config.BOT_NAME} v{Config.VERSION}")

    # 🔥 FIX: context_memory ကို လက်ခံအောင် ပြင်လိုက်ပြီ
    async def chat(self, user_input: str, user_id: int = 0, chat_history: list = [], context_memory: str = "") -> str:
        """The Main Loop"""
        logger.info(f"📩 User ({user_id}): {user_input}")

        # --- STEP 1: THINK ---
        # Brain ကို Context ပါ ထည့်ပေးလိုက်မယ်
        response = self.brain.think(user_input, chat_history, context_memory)

        try:
            function_call = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_call = part.function_call
                        break 

            # --- CASE A: Direct Text Response ---
            if not function_call:
                return self._extract_text(response)

            # --- CASE B: Tool Execution ---
            else:
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                logger.info(f"🛠️ Brain requires tool: {tool_name} | Args: {tool_args}")
                
                # Run Tool
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                # --- SELF-CORRECTION LOOP ---
                if tool_name == "shell_exec" and self._is_error(tool_result):
                    logger.warning(f"⚠️ Error detected via Shell. Activating Reflector...")
                    fix_command = self.reflector.reflect_and_fix(
                        task=user_input,
                        failed_command=tool_args.get("command"),
                        error_log=tool_result
                    )
                    if fix_command:
                        logger.info(f"🚑 Retrying with Fixed Command: {fix_command}")
                        tool_result = await self._execute_tool("shell_exec", {"command": fix_command})
                        tool_result += f"\n\n(✨ SYSTEM NOTE: Auto-fixed via Reflector Protocol.)"

                # Brain ကို အဖြေပြန်ပေးမယ် (Strict Prompt)
                final_response = self.brain.think(
                    user_input=f"""
                    SYSTEM REPORT: 
                    - User asked: '{user_input}'
                    - Tool used: '{tool_name}'
                    - Tool Output: {tool_result}
                    
                    INSTRUCTION: 
                    - Based ONLY on the Tool Output above, provide the final answer to the user in Burmese.
                    - If the search result has a direct answer (e.g., '32°C'), use it!
                    - DO NOT use any more tools.
                    """,
                    chat_history=chat_history
                )
                
                result_text = self._extract_text(final_response)
                
                if result_text == "...":
                    return f"System processing completed. (Tool Output: {str(tool_result)[:100]})."
                
                return result_text

        except Exception as e:
            logger.error(f"❌ Critical Error: {e}")
            return f"System Error: {str(e)}"

    def _is_error(self, result: str) -> bool:
        error_signals = ["STDERR", "Error:", "Traceback", "Exception", "TIMEOUT ALERT", "SAFETY ALERT", "command not found"]
        return any(signal in result for signal in error_signals)

    def _extract_text(self, response):
        text_parts = []
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
        return "\n".join(text_parts) if text_parts else "..."

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
     """Tool Execution Hub (Powered by Registry)"""
     # ရလာတဲ့ Tool နာမည်နဲ့ Data ကို Registry ဆီ လှမ်းပို့လိုက်ရုံပဲ၊ သူဘာသာ အကုန်လုပ်သွားမယ်
     return await tool_registry.execute_tool(tool_name, **args)