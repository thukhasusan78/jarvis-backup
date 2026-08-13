import logging
import os
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_DELEGATOR")

class DelegateTaskTool(BaseTool):
    """
    Manager Tool for the CEO to delegate tasks to specialized Sub-Agents.
    """
    name = "delegate_task"
    description = "Delegate complex tasks to specialized Sub-Agents (sysadmin, researcher). The CEO must use this to assign workload instead of doing it manually."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "agent_role": types.Schema(
                type=types.Type.STRING,
                enum=["sysadmin", "researcher"],
                description="Delegate strictly to: 'sysadmin' for terminal/Linux/server tasks, 'researcher' for news/web search/research."
            ),
            "task_prompt": types.Schema(
                type=types.Type.STRING,
                description="The exact task to perform. CRITICAL: You MUST include the full END-GOAL of the user here (e.g., 'Research this AND trigger the content writer to post it'), so the sub-agent knows what the next step in the pipeline is."
            )
        }

    def get_required(self) -> List[str]:
        return ["agent_role", "task_prompt"]

    async def execute(self, **kwargs) -> str:
        role = kwargs.get("agent_role")
        task = kwargs.get("task_prompt")

        logger.info(f"👔 CEO Delegating task to {role.upper()}...")

        # 👈 FIX: Hardcode မသုံးတော့ဘဲ core/prompts/ အောက်က ဖိုင်များကိုသာ အလိုအလျောက် ဖတ်မည်
        prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', f'{role}.md')
        
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_instruction = f.read()
        else:
            system_instruction = "You are a specialized Assistant."

        # --- 🌐 THE SQUARE (SHARED INTERNAL FEED) INJECTION ---
        square_path = os.path.join("workspace", "square.md")
        square_context = ""
        
        # အခြား Agent များ တင်ထားသော နောက်ဆုံး လုပ်ဆောင်ချက်များကို ဖတ်မည်
        if os.path.exists(square_path):
            with open(square_path, "r", encoding="utf-8") as f:
                # Token မများအောင် နောက်ဆုံး စာလုံးရေ ၈၀၀၀ ကိုသာ ယူမည်
                square_context = f.read()[-8000:] 
                
        system_instruction += f"""
        YOUR ASSIGNED MISSION:
        {task}
        
        [🌐 THE INTERNAL SQUARE FEED (Recent Team Activity)]:
        {square_context if square_context else "No recent activity."}
        
        CRITICAL RULE (EVENT-DRIVEN HANDOFF):
        When you have completed your part of the mission, YOU MUST NOT STOP SILENTLY. 
        You MUST use the `publish_event` tool to pass your results to the next logical agent (e.g., from 'researcher' to 'deep_researcher', or to 'ceo' for final reporting).
        If you are the final step in the entire pipeline, use `publish_event` with target_agent='ceo' and event_type='WORKFLOW_COMPLETED'.
        """

        try:
            from core.agent import JarvisAgent
            import asyncio
            worker_agent = JarvisAgent(role=role)
            worker_agent.brain.system_instruction = system_instruction
            
            # 🚀 Fire and Forget (CEO က မစောင့်တော့ဘဲ နောက်ကွယ်ကနေ Run ခိုင်းလိုက်မည်)
            asyncio.create_task(worker_agent.chat(f"Execute mission: {task}", user_id=999999)) 
            
            return f"✅ Mission successfully assigned to {role.upper()} in the background. You can now report to the Sir that the team is working on it."
            
        except Exception as e:
            logger.error(f"Delegation Error: {e}")
            return f"Error from {role}: {str(e)}"