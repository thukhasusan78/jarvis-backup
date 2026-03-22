import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from memory.memory_controller import memory_controller
from config import Config

logger = logging.getLogger("JARVIS_TASK_TOOL")

class TaskTool(BaseTool):
    """
    Manage ongoing tasks and long-term projects.
    """
    name = "manage_task"
    description = "Manage ongoing tasks or projects for the Sir. Use this to remember what you and the Sir are currently working on. You can 'add', 'list', or 'remove' tasks."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["add", "list", "remove"],
                description="Action to perform: 'add' a new task, 'list' ongoing tasks, or 'remove' a completed task."
            ),
            "task_description": types.Schema(
                type=types.Type.STRING,
                description="Description of the task or project (required for 'add')."
            ),
            "task_id": types.Schema(
                type=types.Type.INTEGER,
                description="ID of the task to remove (required for 'remove')."
            )
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        user_id = Config.ALLOWED_USER_ID
        
        try:
            if action == "add":
                desc = kwargs.get("task_description")
                if not desc:
                    return "Error: 'task_description' is required to add a task."
                
                if memory_controller.add_task(user_id, desc):
                    return f"✅ Ongoing task added: {desc}"
                return "❌ Failed to add ongoing task."
                
            elif action == "list":
                tasks = memory_controller.get_tasks(user_id)
                if tasks:
                    return tasks
                return "No ongoing tasks at the moment."
                
            elif action == "remove":
                t_id = kwargs.get("task_id")
                if not t_id:
                    # ID မသိရင် User ကို List အရင်ပြမယ်
                    tasks = memory_controller.get_tasks(user_id)
                    return f"Error: 'task_id' is required to remove a task. Current tasks:\n{tasks}"
                
                if memory_controller.remove_task(t_id):
                    return f"✅ Task [{t_id}] marked as completed and removed."
                return f"❌ Failed to remove task ID [{t_id}]."
                
            else:
                return f"Error: Unknown action '{action}'."
                
        except Exception as e:
            logger.error(f"Task Tool Error: {e}")
            return f"Task Tool Error: {str(e)}"