import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from config import Config
from memory.db_manager import db_manager

logger = logging.getLogger("JARVIS_MEMORY_TOOL")

class RememberFactTool(BaseTool):
    """
    Store a permanent fact about the user to Long-term Memory.
    """
    name = "remember_fact"
    description = "Store a permanent fact about the user (e.g., Name, Location, Preferences). Use this when user introduces themselves."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "fact_type": types.Schema(
                type=types.Type.STRING, 
                description="The category (e.g., 'Name', 'Job', 'Location')"
            ),
            "fact_value": types.Schema(
                type=types.Type.STRING, 
                description="The actual fact (e.g., 'Mg Mg', 'Yangon')"
            )
        }

    def get_required(self) -> List[str]:
        return ["fact_type", "fact_value"]

    async def execute(self, **kwargs) -> str:
        key = kwargs.get("fact_type")
        val = kwargs.get("fact_value")
        
        if not key or not val:
            return "Error: Both 'fact_type' and 'fact_value' are required."
            
        # User ID ကို Config ကနေပဲ ယူသုံးမယ် (မူရင်းအတိုင်း)
        user_id = Config.ALLOWED_USER_ID 
        
        try:
            if db_manager.update_profile(user_id, key, val):
                return f"✅ Saved to Long-term Memory: {key} = {val}"
            return "Error saving fact to database."
        except Exception as e:
            logger.error(f"Memory Tool Error: {e}")
            return f"Memory Tool Error: {str(e)}"