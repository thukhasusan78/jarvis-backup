import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool
from core.message_broker import publish_event

logger = logging.getLogger("JARVIS_PUBLISHER")

class PublishEventTool(BaseTool):
    """Agent များ အလုပ်ပြီးဆုံးပါက Message Broker သို့ Event လွှင့်ရန် Tool"""
    name = "publish_event"
    description = "Publish an event to the Message Broker. Use this when you finish your specific task and need to pass the data to the next agent or manager."
    owner_role = "all"
    is_terminal = True # 🚀 ဒီ Tool သုံးပြီးတာနဲ့ Agent ချက်ချင်း အနားယူမည်

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "event_type": types.Schema(type=types.Type.STRING, description="e.g., 'RESEARCH_DONE', 'CODE_WRITTEN', 'WORKFLOW_COMPLETED'"),
            "target_agent": types.Schema(type=types.Type.STRING, description="The logical next agent or manager (e.g., 'persona_manager', 'content_writer', 'ceo')"),
            "data": types.Schema(
                type=types.Type.STRING, 
                description="CRITICAL: The actual findings, detailed instructions, or full output to pass to the next agent. NEVER leave this blank. If you are passing instructions, write the full prompt here."
            )
        }

    def get_required(self) -> List[str]:
        return ["event_type", "target_agent", "data"]

    async def execute(self, **kwargs) -> str:
        event_type = kwargs.get("event_type")
        target_agent = kwargs.get("target_agent")
        
        # Database ထဲသို့ Event ပစ်ထည့်မည် (Fire and Forget ရဲ့ အစစ်အမှန်)
        publish_event(event_type, target_agent, kwargs)
        # 🌐 Square ထဲသို့ မှတ်တမ်းတင်မည် (User နှင့် အခြား Agent များ မြင်နိုင်ရန်)
        import os
        square_path = os.path.join("workspace", "square.md")
        os.makedirs("workspace", exist_ok=True)
        with open(square_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- 📬 EVENT PUBLISHED: [{event_type}] targetting {target_agent.upper()} ---\nData/Message: {str(kwargs.get('data'))[:1000]}...\n")
        
        return f"✅ Event '{event_type}' published to Message Broker for '{target_agent}'. Your process will now terminate."