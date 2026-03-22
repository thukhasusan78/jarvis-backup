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
            "schedule_type": types.Schema(
                type=types.Type.STRING, 
                enum=["cron", "date"],
                description="Use 'cron' for daily/weekly repeating tasks. Use 'date' for one-time tasks (e.g., 'in 5 minutes')."
            ),
            "cron_expression": types.Schema(
                type=types.Type.STRING, 
                description="For 'cron' type: 'min hour day month week' (e.g., '0 8 * * *'). Leave empty if type is 'date'."
            ),
            "run_at": types.Schema(
                type=types.Type.STRING, 
                description="For 'date' type: Exact future time in 'YYYY-MM-DD HH:MM:SS' format (Asia/Yangon time). Leave empty if type is 'cron'."
            ),
            "job_id": types.Schema(
                type=types.Type.STRING, 
                description="Unique ID for the job"
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
                sched_type = kwargs.get("schedule_type", "cron")
                cron = kwargs.get("cron_expression")
                run_at = kwargs.get("run_at")
                jid = kwargs.get("job_id")
                
                if not prompt: return "Error: 'task_prompt' is required."
                if sched_type == "cron" and not cron: return "Error: 'cron_expression' is required for cron type."
                if sched_type == "date" and not run_at: return "Error: 'run_at' is required for date type."

                if not jid or jid == "auto_task":
                    jid = f"task_{uuid.uuid4().hex[:6]}"
                
                return scheduler.add_task(
                    prompt=prompt, 
                    user_id=Config.ALLOWED_USER_ID, 
                    job_id=jid, 
                    schedule_type=sched_type, 
                    cron_str=cron, 
                    run_at=run_at
                )
            
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