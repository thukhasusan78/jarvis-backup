import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from memory.memory_controller import memory_controller

logger = logging.getLogger("JARVIS_PERSONA_MANAGER")

class PersonaManagerTool(BaseTool):
    """
    Manage and retrieve AI writing Personas/Styles from the Vector Database.
    """
    name = "manage_persona"
    description = "Save a new writing persona/style or load an existing one from the Vector DB. Used to make the Content Writer sound like a specific human creator."
    # CEO (Sysadmin) က သိမ်းဖို့သုံးမယ်၊ Content Writer က ပြန်ဆွဲထုတ်ဖို့ သုံးမယ်
    owner_role = ["ceo", "sysadmin", "content_writer"]

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["save", "load"],
                description="Action to perform: 'save' a new persona, or 'load' an existing one."
            ),
            "persona_name": types.Schema(
                type=types.Type.STRING,
                description="The name of the persona (e.g., 'Tech_Blogger', 'YouTube_Tech_Guru')."
            ),
            "style_description": types.Schema(
                type=types.Type.STRING,
                description="The detailed writing style, tone, and examples. (Required only for 'save' action)."
            )
        }

    def get_required(self) -> List[str]:
        return ["action", "persona_name"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        persona_name = kwargs.get("persona_name")
        style_description = kwargs.get("style_description", "")

        try:
            if action == "save":
                if not style_description:
                    return "❌ Error: 'style_description' is required to save a persona."
                
                # Vector DB ထဲသို့ Persona Category ဖြင့် သိမ်းဆည်းခြင်း
                success = memory_controller.save_knowledge(
                    category="Persona", 
                    task=persona_name, 
                    solution=style_description, 
                    code_snippet=""
                )
                
                if success:
                    logger.info(f"🎭 Persona Saved: {persona_name}")
                    return f"✅ Success: Persona '{persona_name}' saved to Deep Memory. The Writer Agent can now use this style."
                else:
                    return f"❌ Error: Failed to save Persona '{persona_name}' to Vector DB."
                    
            elif action == "load":
                # Vector DB ထဲမှ Persona အတိအကျကို ပြန်ရှာခြင်း
                query = f"Persona: {persona_name}"
                result = memory_controller.search_knowledge(query)
                
                if result:
                    logger.info(f"🎭 Persona Loaded: {persona_name}")
                    return f"🎭 [PERSONA STYLE DATA FOR '{persona_name}']\n{result}"
                else:
                    return f"❌ Warning: No persona found for '{persona_name}'. Please save it first or use a default writing style."

        except Exception as e:
            logger.error(f"Persona Manager Error: {e}")
            return f"Error executing Persona Manager: {str(e)}"