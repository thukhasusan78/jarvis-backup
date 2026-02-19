import uuid
import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from config import Config

logger = logging.getLogger("JARVIS_SCHEDULE_TOOL")

class ScheduleTool(BaseTool):
    """
    Manage Cron-based Scheduled Tasks.
    """
    name = "manage_schedule"
    description = "Schedule a new task or remove an existing one using Cron format."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING, 
                enum=["add", "remove", "list"],
                description="What action to perform: 'add', 'remove', or 'list'"
            ),
            "task_prompt": types.Schema(
                type=types.Type.STRING, 
                description="What Jarvis should do (e.g., 'Check weather')"
            ),
            "cron_expression": types.Schema(
                type=types.Type.STRING, 
                description="Cron format: 'min hour day month week' (e.g., '0 8 * * *' for daily 8am)"
            ),
            "job_id": types.Schema(
                type=types.Type.STRING, 
                description="Unique ID for the job (e.g., 'weather_daily')"
            )
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        from core.scheduler import jarvis_scheduler
        action = kwargs.get("action")
        scheduler = jarvis_scheduler 
        
        try:
            if action == "add":
                prompt = kwargs.get("task_prompt")
                cron = kwargs.get("cron_expression")
                jid = kwargs.get("job_id")
                
                if not prompt or not cron:
                    return "Error: 'task_prompt' and 'cron_expression' are required to add a task."

                # 🔥 FIX: ID မပေးရင် Auto Unique ID ထုတ်ပေးမယ် (မူရင်း Logic အတိုင်း)
                if not jid or jid == "auto_task":
                    jid = f"task_{uuid.uuid4().hex[:6]}"
                
                return scheduler.add_task(prompt, Config.ALLOWED_USER_ID, cron, jid)
            
            elif action == "remove":
                jid = kwargs.get("job_id")
                # ID မသိရင် User ကို List အရင်ကြည့်ခိုင်းမယ်
                if not jid: 
                    tasks = scheduler.list_tasks()
                    return f"Error: Please provide the Task ID to remove. Here are active tasks:\n{tasks}"
                return scheduler.remove_task(jid)
            
            elif action == "list":
                return scheduler.list_tasks()
            
            else:
                return f"Error: Unknown action '{action}'."

        except Exception as e:
            return f"Schedule Tool Error: {str(e)}"