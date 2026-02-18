import os
import time
import logging
from google import genai
from google.genai import types
from config import Config

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
        
        # Tool Definitions (AI သိအောင် ကြေညာခြင်း - လက်တွေ့ run မှာက agent.py မှာ)
        self.tools_config = [
            types.Tool(
                function_declarations=[
                    # 1. Search Web (Tavily)
                    types.FunctionDeclaration(
                        name="search_web",
                        description="Search the internet for real-time information, news, or coding solutions.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"query": types.Schema(type=types.Type.STRING)},
                            required=["query"]
                        )
                    ),
                    # 2. Browser Navigation (Playwright)
                    types.FunctionDeclaration(
                        name="browser_nav",
                        description="Navigate to a specific URL using a headless browser.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"url": types.Schema(type=types.Type.STRING)},
                            required=["url"]
                        )
                    ),
                    # 3. Read Page Content (BeautifulSoup)
                    types.FunctionDeclaration(
                        name="read_page_content",
                        description="Read text content from the currently open webpage (RAM saving mode).",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={}, # No params needed, reads current page
                        )
                    ),
                    # 4. Shell Execution (The Body)
                    types.FunctionDeclaration(
                        name="shell_exec",
                        description="Execute Linux terminal commands on the VPS. USE WITH CAUTION.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"command": types.Schema(type=types.Type.STRING)},
                            required=["command"]
                        )
                    ),
                    # 5. File Read
                    types.FunctionDeclaration(
                        name="file_read",
                        description="Read code or text from a specific file path.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"path": types.Schema(type=types.Type.STRING)},
                            required=["path"]
                        )
                    ),
                    # 6. File Write
                    types.FunctionDeclaration(
                        name="file_write",
                        description="Write code or content to a file. Overwrites existing content.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(type=types.Type.STRING),
                                "content": types.Schema(type=types.Type.STRING)
                            },
                            required=["path", "content"]
                        )
                    ),
                    # 7. PIP Install (Self-Upgrade)
                    types.FunctionDeclaration(
                        name="pip_install",
                        description="Install new Python libraries if needed.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"package": types.Schema(type=types.Type.STRING)},
                            required=["package"]
                        )
                    ),
                    # 8. Check Resources (Health)
                    types.FunctionDeclaration(
                        name="check_resource",
                        description="Check current RAM, CPU usage and Disk space.",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={})
                    ),
                    # 9. Screen Capture (Visual Debug)
                    types.FunctionDeclaration(
                        name="screen_capture",
                        description="Take a screenshot of the browser to see what's happening.",
                        parameters=types.Schema(type=types.Type.OBJECT, properties={})
                    ),
                    # 10. Remember Skill (Long-term Memory)
                    types.FunctionDeclaration(
                        name="remember_skill",
                        description="Save a successful solution or method to long-term memory/skills library.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "task": types.Schema(type=types.Type.STRING),
                                "solution": types.Schema(type=types.Type.STRING),
                                "code_snippet": types.Schema(type=types.Type.STRING)
                            },
                            required=["task", "solution"]
                        )
                    ),

                    # 11. Manage Schedule
                    types.FunctionDeclaration(
                        name="manage_schedule",
                        description="Schedule a new task or remove an existing one using Cron format.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "action": types.Schema(type=types.Type.STRING, enum=["add", "remove", "list"]),
                                "task_prompt": types.Schema(type=types.Type.STRING, description="What Jarvis should do (e.g., 'Check weather')"),
                                "cron_expression": types.Schema(type=types.Type.STRING, description="Cron format: 'min hour day month week' (e.g., '0 8 * * *' for daily 8am)"),
                                "job_id": types.Schema(type=types.Type.STRING, description="Unique ID for the job (e.g., 'weather_daily')")
                            },
                            required=["action"]
                        )
                    ),

                    # 12. Git Backup 
                    types.FunctionDeclaration(
                        name="backup_code",
                        description="Backup current project code to GitHub repository.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "message": types.Schema(type=types.Type.STRING, description="Commit message (optional)")
                            },
                            required=[]
                        )
                    ),
                ]
            )
        ]

    def _build_system_instruction(self):
        """Jarvis ၏ Persona နှင့် စည်းမျဉ်းများ (Updated Logic)"""
        return """
        You are JARVIS, an advanced autonomous AI agent running on a Linux VPS.
        
        🔥 CRITICAL PROTOCOL (READ CAREFULLY):
        
        1. DETECT INTENT (DO vs SCHEDULE):
           - If user says "Check weather NOW" -> Use `search_web`.
           - If user says "Check weather EVERY DAY/WEEK/HOUR" -> You MUST use `manage_schedule`.
           - NEVER execute a task immediately if the user asks for a recurring schedule.
        
        2. SCHEDULING RULES:
           - When using `manage_schedule`, convert user's time into CRON format.
           - Examples:
             * "Every morning at 8am" -> "0 8 * * *"
             * "Every 10 minutes" -> "*/10 * * * *"
             * "Every Monday" -> "0 0 * * 1"
           - If user asks for "Seconds" (e.g., 30s) and your tool only supports Minutes, warn them but try your best or set to 1 minute ("* * * * *").

        3. CORE PROTOCOL (REFLEXION MODEL):
           - PLAN: Think step-by-step.
           - ACT: Use provided tools.
           - REFLECT: If error, fix it yourself.
        
        4. TOOLS USAGE:
           - Use `search_web` for real-time info.
           - Use `shell_exec` for VPS control.
           - Use `manage_schedule` for ANY recurring task.

        5. SERVER ADMIN ROLE:
           - You have FULL ROOT ACCESS to the VPS via `shell_exec`.
           - If user asks "Why is RAM high?", use `check_resource` to see specific processes, then explain which APP is the cause.
           - If a service (like nginx) is down, use `shell_exec` to restart it (`systemctl restart nginx`).
           - ACT like a Senior SysAdmin. Fix problems autonomously.   
        
        Response Format:
        - If scheduling, simply confirm: "Task scheduled: [Task Name] at [Time]."
        - Do not hallucinate that you did the task if you only scheduled it. Reply in Burmese.
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