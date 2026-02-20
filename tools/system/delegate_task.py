import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from core.agent import JarvisAgent  # Agent ကို ထပ်မံခေါ်ယူအသုံးပြုမည်

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
                enum=["web_surfer", "sysadmin", "researcher"],
                description="'web_surfer' for browser/social media, 'sysadmin' for terminal/files, 'researcher' for web searches."
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

        # ဌာနအလိုက် System Prompt များကို သီးသန့် ခွဲထုတ်သတ်မှတ်ခြင်း
        personas = {
            "web_surfer": "You are the Web Surfer Sub-Agent. Your ONLY job is to navigate browsers, solve captchas, and interact with websites. Use 'browser_navigate' and 'browser_visual' exclusively.",
            "sysadmin": "You are the SysAdmin Sub-Agent. Your ONLY job is to execute terminal commands, manage files, and check system security. Use 'shell_exec', 'manage_file', and 'check_resource'.",
            "researcher": "You are the Researcher Sub-Agent. Your ONLY job is to find information on the internet. Use 'search_web' and 'read_page_content'."
        }

        system_instruction = personas.get(role, "You are a specialized Assistant.")
        system_instruction += f"\n\nYOUR ASSIGNED MISSION:\n{task}\n\nExecute this mission using your tools and report the final result back to the CEO."

        try:
            # Sub-Agent အသစ်တစ်ခုကို သီးသန့် ဉာဏ်ရည်ဖြင့် မွေးဖွားခြင်း
            worker_agent = JarvisAgent(role=role)
            worker_agent.system_prompt = system_instruction # CEO ရဲ့ ဉာဏ်ကိုဖျက်ပြီး Worker ဉာဏ် ထည့်ခြင်း
            
            # Sub-Agent ကို အလုပ်ခိုင်းခြင်း
            result = await worker_agent.chat(f"Execute mission: {task}", user_id=999999) # ID သီးသန့်ခွဲထားမည်
            
            return f"[{role.upper()} REPORT]:\n{result}"
        except Exception as e:
            logger.error(f"Delegation Error: {e}")
            return f"Error from {role}: {str(e)}"