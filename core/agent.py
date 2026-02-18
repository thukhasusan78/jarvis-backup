import logging
import json
import traceback
import psutil # RAM စစ်ဖို့အတွက်
from typing import Dict, Any

# Core Modules
from core.brain import JarvisBrain
from config import Config

# --- TOOLS IMPORT (ရေးပြီးသား Tool တွေကို လှမ်းချိတ်ခြင်း) ---
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

# Shell Tool (VPS Control)
try:
    from tools.system.shell import execute_command
except ImportError:
    execute_command = None

# Scraper Tool (Web Reader)
try:
    from tools.web.scraper import read_url
except ImportError:
    read_url = None

# Resource Tool အသစ်ကို လှမ်းခေါ်မယ်
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
        """Jarvis Agent - The Executor"""
        logger.info("🤖 Initializing Jarvis Agent...")
        self.brain = JarvisBrain()
        
        # Tavily Setup
        if hasattr(Config, 'TAVILY_KEY') and Config.TAVILY_KEY:
            self.tavily = TavilyClient(api_key=Config.TAVILY_KEY)
        else:
            logger.warning("⚠️ Tavily API Key missing.")
            self.tavily = None

        logger.info(f"✅ Agent Online: {Config.BOT_NAME} v{Config.VERSION}")

    async def chat(self, user_input: str, user_id: int = 0, chat_history: list = []) -> str:
        """The Main Loop"""
        logger.info(f"📩 User ({user_id}): {user_input}")

        # --- STEP 1: THINK ---
        response = self.brain.think(user_input, chat_history)

        try:
            # Function Call ရှာဖွေခြင်း (Loop ပတ်ပြီးရှာမလို့ "..." ပြဿနာမတက်တော့ဘူး)
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
                tool_args = function_call.args
                logger.info(f"🛠️ Brain requires tool: {tool_name} | Args: {tool_args}")
                
                # Tool Run မယ်
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                # Brain ကို အဖြေပြန်ပေးမယ်
                final_response = self.brain.think(
                    user_input=f"SYSTEM REPORT: User asked '{user_input}'. You used tool '{tool_name}'. Output: {tool_result}. Now give the final answer to user.",
                    chat_history=chat_history
                )
                return self._extract_text(final_response)

        except Exception as e:
            logger.error(f"❌ Critical Error: {e}")
            return f"System Error: {str(e)}"

    def _extract_text(self, response):
        """Text သီးသန့်ဆွဲထုတ်နည်း"""
        text_parts = []
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
        return "\n".join(text_parts) if text_parts else "..."

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Tool ၁၀ မျိုးလုံးကို ခွဲခြားစိတ်ဖြာပြီး အလုပ်လုပ်မယ့်နေရာ
        """
        try:
            # 1. SEARCH WEB (Tavily)
            if tool_name == "search_web":
                query = args.get("query")
                if not self.tavily: return "Error: Tavily Key missing."
                results = self.tavily.search(query=query, search_depth="basic")
                return json.dumps(results)[:2000]

            # 2. CHECK RESOURCE (UPDATED - GOD MODE)
            elif tool_name == "check_resource":
                if get_system_status:
                    return get_system_status()
                return "Error: Resource tool file missing."

            # 3. SHELL EXEC (Linux Command)
            elif tool_name == "shell_exec":
                command = args.get("command")
                if execute_command:
                    return execute_command(command)
                return "Error: Shell tool file missing."

            # 4. READ PAGE CONTENT (Scraper)
            elif tool_name == "read_page_content":
                # URL ကို args ထဲကနေ ရှာမယ် (တခါတလေ args မပါရင် current context လိုတယ်)
                # လောလောဆယ် User ပေးတဲ့ URL ကို ဖတ်ဖို့ logic ထည့်ထားမယ်
                url = args.get("url") 
                if not url: return "Error: No URL provided to read."
                if read_url:
                    return read_url(url)
                return "Error: Scraper tool file missing."

            # 8. MANAGE SCHEDULE
            elif tool_name == "manage_schedule":
                from core.scheduler import jarvis_scheduler
                action = args.get("action")
                scheduler = jarvis_scheduler 
                
                if action == "add":
                    prompt = args.get("task_prompt")
                    cron = args.get("cron_expression")
                    jid = args.get("job_id", "auto_task")
                    # User ID ကို Agent ရဲ့ chat method ကနေ ယူရမယ်၊ ဒါပေမဲ့ ဒီ tool call မှာ မပါလာဘူး
                    # Config.ALLOWED_USER_ID ကိုပဲ default သုံးလိုက်မယ်
                    return scheduler.add_task(prompt, Config.ALLOWED_USER_ID, cron, jid)
                
                elif action == "remove":
                    jid = args.get("job_id")
                    return scheduler.remove_task(jid)
                
                elif action == "list":
                    return scheduler.list_tasks()  

            # 9. GIT BACKUP
            elif tool_name == "backup_code":
                msg = args.get("message")
                if backup_code:
                    return backup_code(msg)
                return "Error: Git backup tool missing."          

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