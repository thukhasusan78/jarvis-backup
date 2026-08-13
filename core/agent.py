import logging
import asyncio
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
    def __init__(self, role: str = "ceo"):
        """Jarvis Agent - The Executive Manager"""
        self.role = role
        logger.info(f"🤖 Initializing Agent [{self.role.upper()}]...")
        
        # Agent အသစ်နိုးလာတိုင်း Tool အသစ်တွေ ရှိမရှိ အမြဲစစ်မယ် (Auto Reload Magic)
        tool_registry.reload_custom_tools()
        
        # Brain ဆီကို Role အတိအကျ ပို့ပေးမယ်
        self.brain = JarvisBrain(role=self.role)
        self.reflector = JarvisReflector()

        logger.info(f"✅ Agent Online: {Config.BOT_NAME} v{Config.VERSION}")

    async def chat(self, user_input: str, user_id: int = 0, chat_history: list = [], context_memory: str = "", send_status=None, task_id: str = None) -> str:
        """The Main Loop (Event-Driven State Machine via Markdown)"""
        import os
        
        # ၁။ Task File တည်ဆောက်ခြင်း (OpenClaw စနစ်)
        if not task_id:
            # Task ID မပါလာရင် (Sub-Agent တွေဖြစ်နေရင်) ဖိုင်အသစ် မဆောက်တော့ဘဲ Temporary Memory ကိုပဲ သုံးမယ်
            task_id = "sub_agent_task"
            task_file = None
        else:
            task_dir = os.path.abspath(os.path.join("workspace", "tasks", "pending"))
            os.makedirs(task_dir, exist_ok=True)
            task_file = os.path.join(task_dir, f"{task_id}.md")

        # ၂။ ဖိုင်အသစ်ဆိုရင် ခေါင်းစဉ်တပ်မယ်၊ အဟောင်းရှိရင် မှတ်ဉာဏ်ပြန်ဖတ်မယ်
        if task_file:
            if not os.path.exists(task_file):
                with open(task_file, "w", encoding="utf-8") as f:
                    f.write(f"# Task ID: {task_id}\n**User Request:** {user_input}\n\n## Execution Log\n")
                current_task_context = user_input
            else:
                with open(task_file, "r", encoding="utf-8") as f:
                    current_task_context = f.read()
                    current_task_context += f"\n\n[SYSTEM: Resuming interrupted task. Continue from the last step.]\n"
        else:
            current_task_context = user_input # Sub-agent အတွက် ဖိုင်မရှိရင် Memory ပေါ်မှာပဲ သိမ်းမယ်

        logger.info(f"📩 Processing Task: {task_id}")

        max_loops = 15 
        loop_count = 0
        last_tool_name = None
        repeat_count = 0

        # ၃။ Event Loop စတင်ခြင်း
        while loop_count < max_loops:
            loop_count += 1
            try:
                # --- THINK (Brain ကို စဉ်းစားခိုင်းမယ်) ---
                response = await asyncio.to_thread(self.brain.think, current_task_context, chat_history, context_memory)

                if isinstance(response, str):
                    logger.warning(f"⚠️ Brain Error: {response}")
                    if task_file:
                        with open(task_file, "a", encoding="utf-8") as f:
                            f.write(f"\n[ERROR] Brain API Failed: {response}\n")
                    return f"API အခက်အခဲဖြစ်နေပါသည်။ Error: {response}"

                function_call = None
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if not candidate.content:
                        return "ဆရာ၊ Safety Filter ကြောင့် ပိတ်ခံလိုက်ရပါသည်။"
                    if candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.function_call:
                                function_call = part.function_call
                                break

                # --- CASE A: အလုပ်ပြီးစီးသွားခြင်း (Final Answer) ---
                if not function_call:
                    final_text = self._extract_text(response)
                    if task_file:
                        with open(task_file, "a", encoding="utf-8") as f:
                            f.write(f"\n### ✅ FINAL OUTPUT\n{final_text}\n")
                    return final_text

                # --- CASE B: Tool ဆက်သုံးခြင်း (မှတ်တမ်းတင်မည်) ---
                tool_name = function_call.name
                tool_args = dict(function_call.args)

                if task_file:
                    with open(task_file, "a", encoding="utf-8") as f:
                        f.write(f"\n### 🛠️ Step {loop_count}: Using `{tool_name}`\n")
                        f.write(f"**Arguments:** {tool_args}\n")

                # ၄။ Anti-Loop Protocol (အဆုံးမဲ့ သံသရာလည်ခြင်းကို ဖြတ်တောက်မည်)
                if tool_name == last_tool_name:
                    repeat_count += 1
                else:
                    repeat_count = 0
                    last_tool_name = tool_name

                if repeat_count >= 2:
                    error_msg = f"🛑 [ANTI-LOOP TRIGGERED] Stopped repeating action: {tool_name}."
                    if task_file:
                        with open(task_file, "a", encoding="utf-8") as f:
                            f.write(f"**Result:** {error_msg}\n")
                    current_task_context += f"\n\n[SYSTEM: {error_msg} DO NOT REPEAT THIS TOOL. MOVED TO NEXT STRATEGY.]\n"
                    if send_status: await send_status("🛑 လုပ်ဆောင်ချက် ထပ်နေသဖြင့် အလိုအလျောက် ကျော်ဖြတ်နေပါသည်...")
                    continue 
                
                if send_status:
                    await send_status(f"Executing: {tool_name.replace('_', ' ')}...")

                # ၅။ Tool ကို Run မယ်
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                if not tool_result or str(tool_result).strip() == "":
                    tool_result = "[Success] Command executed silently."

                if task_file:
                    with open(task_file, "a", encoding="utf-8") as f:
                        f.write(f"**Result:**\n```\n{tool_result}\n```\n")

                # --- 🛑 DYNAMIC HARD STOP (SCALABLE ARCHITECTURE) ---
                # Tool က "is_terminal = True" ဖြစ်ခဲ့ရင် AI ကို ဆက်မတွေးခိုင်းတော့ဘဲ ချက်ချင်း Loop ဖြတ်မည်
                tool_instance = tool_registry.get_tool(tool_name)
                if tool_instance and getattr(tool_instance, "is_terminal", False):
                    logger.info(f"🛑 Terminal Tool '{tool_name}' executed. Exiting loop smoothly.")
                    if task_file:
                        with open(task_file, "a", encoding="utf-8") as f:
                            f.write(f"\n### ✅ WORKFLOW HANDED OVER OR COMPLETED\n")
                    return tool_result
                # ---------------------------------------

                # ၆။ Reflector (Error တက်လျှင် အလိုလို ပြင်ဆင်မည်)
                if tool_name == "shell_exec" and self._is_error(tool_result):
                    if send_status: await send_status("🚑 Error ကို အလိုအလျောက် ပြင်ဆင်နေပါသည်...")
                    fix_command = self.reflector.reflect_and_fix(current_task_context, tool_args.get("command"), tool_result)
                    if fix_command:
                        tool_result = await self._execute_tool("shell_exec", {"command": fix_command})
                        if task_file:
                            with open(task_file, "a", encoding="utf-8") as f:
                                f.write(f"\n### 🚑 Auto-Fix Applied\n**Command:** `{fix_command}`\n**Result:**\n```\n{tool_result}\n```\n")
                        tool_result += "\n(✨ SYSTEM NOTE: Auto-fixed via Reflector Protocol.)"

                # Context ထဲ ပြန်ထည့်ပြီး နောက်တစ်ပတ် ပြန်စဉ်းစားခိုင်းမယ်
                current_task_context += f"\n\n[SYSTEM: Tool '{tool_name}' executed. Output:\n{tool_result}]\n\n⚠️ CRITICAL: If the goal is met, DO NOT call tools again. Reply to the user directly."

            except Exception as e:
                logger.error(f"❌ Error in Task Loop: {e}")
                if task_file:
                    with open(task_file, "a", encoding="utf-8") as f:
                        f.write(f"\n### ❌ SYSTEM CRASH\n{str(e)}\n")
                return f"System Error: {str(e)}"
                
        # Loop ပတ်တာ များသွားရင် ရပ်မယ် (အကုန် မပျောက်သွားဘဲ ဖိုင်ထဲမှာ ကျန်ခဲ့မယ်)
        if task_file:
            with open(task_file, "a", encoding="utf-8") as f:
                f.write(f"\n### 🛑 TASK PAUSED (MAX LOOPS REACHED)\n")
        return f"အလုပ်မှာ အဆင့်များလွန်းသဖြင့် ရပ်နားလိုက်ပါသည်။ (Task ID: {task_id} တွင် မှတ်တမ်းတင်ထားပါသည်)"

    def _is_error(self, result: str) -> bool:
        error_signals = ["STDERR", "Error:", "Traceback", "Exception", "TIMEOUT ALERT", "SAFETY ALERT", "command not found"]
        return any(signal in result for signal in error_signals)

    def _extract_text(self, response):
        text_parts = []
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
        return "\n".join(text_parts) if text_parts else "..."

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Tool Execution Hub (Powered by Registry) — role enforced at runtime."""
        return await tool_registry.execute_tool(tool_name, caller_role=self.role, **args)