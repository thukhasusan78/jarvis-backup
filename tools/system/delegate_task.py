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
    description = "Delegate complex tasks to specialized Sub-Agents (web_surfer, sysadmin, researcher). The CEO must use this to assign workload instead of doing it manually."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "agent_role": types.Schema(
                type=types.Type.STRING,
                # 🔥 FIX: deep_researcher ကို ထပ်ထည့်ပေးလိုက်သည်
                enum=["web_surfer", "sysadmin", "researcher", "deep_researcher"],
                description="'web_surfer' for browser/social media, 'sysadmin' for terminal/files, 'researcher' for code planning, 'deep_researcher' for content/YouTube research."
            ),
            "task_prompt": types.Schema(
                type=types.Type.STRING,
                description="Clear, detailed instructions for the sub-agent."
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

        system_instruction += f"\n\nYOUR ASSIGNED MISSION:\n{task}\n\nExecute this mission using your tools and report the final result back to the CEO."

        try:
            from core.agent import JarvisAgent
            # Sub-Agent အသစ်တစ်ခုကို သီးသန့် ဉာဏ်ရည်ဖြင့် မွေးဖွားခြင်း
            worker_agent = JarvisAgent(role=role)
            worker_agent.brain.system_instruction = system_instruction
            
            # Sub-Agent ကို အလုပ်ခိုင်းခြင်း
            result = await worker_agent.chat(f"Execute mission: {task}", user_id=999999) # ID သီးသန့်ခွဲထားမည်
            
            return f"[{role.upper()} REPORT]:\n{result}"
        except Exception as e:
            logger.error(f"Delegation Error: {e}")
            return f"Error from {role}: {str(e)}"