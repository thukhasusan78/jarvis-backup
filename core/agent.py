import logging
import json
import traceback
import asyncio
import uuid  # <--- 🔥 NEW: ID အသစ်ထုတ်ပေးဖို့
from typing import Dict, Any

# Core Modules
from core.brain import JarvisBrain
from core.reflector import JarvisReflector
from config import Config
from memory.db_manager import db_manager

# --- TOOLS IMPORT ---
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

try:
    from tools.system.shell import execute_command
except ImportError:
    execute_command = None

try:
    from tools.web.scraper import read_url
except ImportError:
    read_url = None

try:
    from tools.system.resource import get_system_status
except ImportError:
    get_system_status = None    

try:
    from tools.system.git_backup import backup_code
except ImportError:
    backup_code = None    

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_AGENT")

class JarvisAgent:
    def __init__(self):
        """Jarvis Agent - The Executive Manager"""
        logger.info("🤖 Initializing Jarvis Agent (Professional Build)...")
        
        self.brain = JarvisBrain()
        self.reflector = JarvisReflector()
        
        if hasattr(Config, 'TAVILY_KEY') and Config.TAVILY_KEY:
            self.tavily = TavilyClient(api_key=Config.TAVILY_KEY)
        else:
            logger.warning("⚠️ Tavily API Key missing.")
            self.tavily = None

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
        """Tool Execution Hub"""
        try:
            # 1. SEARCH WEB (Updated for Weather)
            if tool_name == "search_web":
                query = args.get("query")
                if not self.tavily: return "Error: Tavily Key missing."
                try:
                    # 🔥 FIX: include_answer=True ထည့်လိုက်ရင် Tavily က အဖြေတို (32°C) ကို အရင်ရှာပေးတယ်
                    results = self.tavily.search(
                        query=query, 
                        search_depth="advanced", 
                        max_results=5,
                        include_answer=True 
                    )
                    return json.dumps(results)[:8000]
                except Exception as e:
                    return f"Search Error: {str(e)}"

            elif tool_name == "check_resource":
                if get_system_status: return get_system_status()
                return "Error: Resource tool file missing."

            elif tool_name == "shell_exec":
                command = args.get("command")
                if execute_command: return execute_command(command)
                return "Error: Shell tool file missing."

            elif tool_name == "read_page_content":
                url = args.get("url") 
                if not url: return "Error: No URL provided."
                if read_url: return read_url(url)
                return "Error: Scraper tool file missing."

            # 8. MANAGE SCHEDULE (Fixed ID Logic)
            elif tool_name == "manage_schedule":
                from core.scheduler import jarvis_scheduler
                action = args.get("action")
                scheduler = jarvis_scheduler 
                
                if action == "add":
                    prompt = args.get("task_prompt")
                    cron = args.get("cron_expression")
                    # 🔥 FIX: ID မပေးရင် Auto ပေးမယ့်အစား Unique ID ထုတ်ပေးမယ်
                    jid = args.get("job_id")
                    if not jid or jid == "auto_task":
                        jid = f"task_{uuid.uuid4().hex[:6]}"
                    
                    return scheduler.add_task(prompt, Config.ALLOWED_USER_ID, cron, jid)
                
                elif action == "remove":
                    jid = args.get("job_id")
                    # ID မသိရင် User ကို List အရင်ကြည့်ခိုင်းမယ်
                    if not jid: 
                        tasks = scheduler.list_tasks()
                        return f"Error: Please provide the Task ID to remove. Here are active tasks:\n{tasks}"
                    return scheduler.remove_task(jid)
                
                elif action == "list":
                    return scheduler.list_tasks()  

            elif tool_name == "backup_code":
                msg = args.get("message")
                if backup_code: return backup_code(msg)
                return "Error: Git backup tool missing." 

            # 10. REMEMBER FACT (Long Term)
            elif tool_name == "remember_fact":
                key = args.get("fact_type")
                val = args.get("fact_value")
                # Config.ALLOWED_USER_ID ကိုပဲ default သုံးမယ်
                user_id = Config.ALLOWED_USER_ID 
                
                if db_manager.update_profile(user_id, key, val):
                    return f"✅ Saved to Long-term Memory: {key} = {val}"
                return "Error saving fact."                      

            # --- အောက်ပါ Tool များသည် ဖိုင်မရှိသေးသဖြင့် Placeholder စာသား ပြန်ပို့မည် ---
            
            elif tool_name == "browser_nav":
                return "Browser Navigation is under construction. Please use 'read_page_content' for now."

            elif tool_name == "screen_capture":
                return "Screen capture module is not installed yet."

            elif tool_name in ["file_read", "file_write"]:
                return "File operations are currently locked for safety."

            elif tool_name == "pip_install":
                return "Self-upgrade (pip install) is disabled in this version."

            elif tool_name == "remember_skill":
                return f"Skill '{args.get('task')}' noted (Memory DB not connected)."

            else:
                return f"Error: Unknown tool '{tool_name}'"

        except Exception as e:
            return f"Tool Execution Error: {str(e)}"