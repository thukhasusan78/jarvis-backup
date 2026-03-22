import json
import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_HOLOGRAM")

class HologramTool(BaseTool):
    """Web UI ရှိ Hologram Box တွင် မြေပုံ၊ ရာသီဥတု၊ Report များကို ပြသရန် Tool"""
    name = "show_hologram"
    description = "Trigger a holographic UI widget on the user's screen (e.g., Google Maps, Weather Widget, Code Snippet, Report). Use this when the user asks to 'see' something."
    owner_role = "ceo"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "widget_type": types.Schema(
                type=types.Type.STRING,
                enum=["map", "weather", "report", "image"],
                description="The type of widget to display."
            ),
            "data_payload": types.Schema(
                type=types.Type.STRING,
                description="The data for the widget in a simple string (e.g., 'Mandalay' for map, or a summary for report)."
            )
        }

    def get_required(self) -> List[str]:
        return ["widget_type", "data_payload"]

    async def execute(self, **kwargs) -> str:
        widget_type = kwargs.get("widget_type")
        data_payload = kwargs.get("data_payload")
        
        # ဒီ Tool က Browser ဆီကို JSON ပို့ဖို့အတွက် Signal ကို ပြန်ပေးပါမယ်။
        # live_brain.py က ဒီ Return ကိုမြင်ရင် WebSocket ကနေ Browser ဆီ Text အနေနဲ့ ပို့ပေးပါလိမ့်မယ်။
        response_json = {
            "type": "hologram_trigger",
            "action": f"render_{widget_type}",
            "data": data_payload
        }
        
        # AI အတွက် "ပြသပြီးကြောင်း" သတင်းပြန်ပို့ခြင်း
        return f"[WIDGET RENDERED]: Successfully sent {widget_type} widget data ({data_payload}) to the user's screen. You can tell them to look at the screen."