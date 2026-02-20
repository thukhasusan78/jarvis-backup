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

    # 🔥 FIX: context_memory နဲ့ Status Update ကို လက်ခံအောင် ပြင်လိုက်ပြီ
    async def chat(self, user_input: str, user_id: int = 0, chat_history: list = [], context_memory: str = "", send_status=None) -> str:
        """The Main Loop (ReAct Architecture)"""
        logger.info(f"📩 User ({user_id}): {user_input}")

        current_task_context = user_input
        max_loops = 15 # Tool အများဆုံး 15 ခါ ဆက်တိုက်သုံးခွင့်ပေးမယ်
        loop_count = 0

        while loop_count < max_loops:
            loop_count += 1
            try:
                # --- THINK ---
                response = self.brain.think(current_task_context, chat_history, context_memory)

                # 🔥 FIX: Brain က API Object အစား စာသား (String) ပြန်ပို့လိုက်ရင် Crash မဖြစ်အောင် ကာကွယ်မယ်
                if isinstance(response, str):
                    logger.warning(f"⚠️ Brain Error Fallback: {response}")
                    if loop_count == 1:
                        return response # ပထမဆုံးအကြိမ်မှာတင် Error တက်ရင် ဆရာ့ဆီ တန်းပို့မယ်
                    else:
                        # Tool တွေသုံးနေရင်း ကြားထဲ Error တက်ရင် ဆက်မလုပ်တော့ဘဲ ရပ်မယ်
                        return f"အလုပ်လုပ်ဆောင်နေစဉ် အခက်အခဲဖြစ်သွားပါသည်။ (Error: {response})"

                function_call = None
                # 🔥 FIX: hasattr သုံးပြီး candidates ရှိမှသာ ဆက်အလုပ်လုပ်အောင် ကာကွယ်မယ်
                if hasattr(response, 'candidates') and response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            function_call = part.function_call
                            break

                # --- CASE A: Direct Text Response (Tool သုံးစရာ မလိုတော့ရင် အဖြေထုတ်ပေးမယ်) ---
                if not function_call:
                    return self._extract_text(response)

                # --- CASE B: Tool Execution (Tool ဆက်သုံးမယ်) ---
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                logger.info(f"🛠️ Loop {loop_count}: Brain requires tool: {tool_name} | Args: {tool_args}")
                
                # 📡 Telegram Status Update (Professional English, No Emojis)
                if send_status:
                    if tool_name == "search_web":
                        query = tool_args.get("query", "data")
                        await send_status(f"Searching web for: {query}...")
                    elif tool_name == "manage_schedule":
                        action = tool_args.get("action", "")
                        task = tool_args.get("task_prompt", "task")
                        if action == "add":
                            await send_status(f"Scheduling task: {task}...")
                        else:
                            await send_status("Managing scheduled tasks...")
                    elif tool_name == "read_page_content":
                        await send_status("Extracting page content...")
                    elif tool_name == "shell_exec":
                        await send_status("Executing system command...")
                    elif tool_name == "manage_knowledge":
                        await send_status("Accessing deep memory...")
                    elif tool_name == "manage_task":
                        await send_status("Managing task queue...")
                    elif tool_name == "check_resource":
                        await send_status("Running system diagnostics...")
                    else:
                        await send_status("Processing request...")

                # Tool ကို Run မယ်
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                # 🔥 ပြင်ဆင်ချက်: Output အလွတ်ဖြစ်နေရင် အောင်မြင်ကြောင်း AI ကို သေချာပြောပြရန်
                if not tool_result or str(tool_result).strip() == "":
                    tool_result = "[Success] Command executed silently with no errors."
                
                # --- SELF-CORRECTION LOOP (For Shell) ---
                if tool_name == "shell_exec" and self._is_error(tool_result):
                    logger.warning(f"⚠️ Error detected. Activating Reflector...")
                    fix_command = self.reflector.reflect_and_fix(
                        task=current_task_context,
                        failed_command=tool_args.get("command"),
                        error_log=tool_result
                    )
                    if fix_command:
                        if send_status:
                            await send_status("🚑 Error တက်သွားသဖြင့် အလိုအလျောက် ပြုပြင်နေပါသည်...")
                        tool_result = await self._execute_tool("shell_exec", {"command": fix_command})
                        tool_result += f"\n\n(✨ SYSTEM NOTE: Auto-fixed via Reflector Protocol.)"

                # Tool ရဲ့ အဖြေကို Context ထဲ ပြန်ထည့်ပြီး နောက်တစ်ပတ် ပြန်စဉ်းစားခိုင်းမယ် (The Loop)
                current_task_context += f"\n\n[SYSTEM: Tool '{tool_name}' executed. Output:\n{tool_result}]\n\n⚠️ CRITICAL INSTRUCTION: If the user's requested task is completely fulfilled, DO NOT call any more tools. Reply directly with the final text answer to the user in Burmese to conclude the task."

            except Exception as e:
                logger.error(f"❌ Critical Error in Loop: {e}")
                return f"System Error: {str(e)}"
                
        return "ခိုင်းစေထားသော အလုပ်မှာ အဆင့်များလွန်းသဖြင့် ရပ်နားလိုက်ပါသည်။"

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