import json
import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_HOLOGRAM")

class HologramTool(BaseTool):
    """Web UI ရှိ Hologram Popup များဖြင့် မြေပုံ၊ ရာသီဥတု၊ Order စာရင်း၊ Report များကို ပြသရန် Tool"""
    name = "show_hologram"
    description = (
        "Trigger a holographic popup widget on the user's web HUD screen while speaking. "
        "Use when the user asks to 'see' something: 'map' (Google Maps location), "
        "'weather' (city name as data), 'orders' (recent Telegram jammer/VIP order data), "
        "'schedule' (upcoming scheduled tasks/reminders), 'tasks' (Sir's ongoing task list), "
        "'sysinfo' (server CPU/RAM/disk vitals), 'report' (text summary), 'image' (image URL/path)."
    )
    owner_role = "ceo"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "widget_type": types.Schema(
                type=types.Type.STRING,
                enum=["map", "weather", "orders", "schedule", "tasks", "sysinfo", "report", "image"],
                description="The type of popup widget to display."
            ),
            "data_payload": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Data for the widget: city/place name for map or weather "
                    "(e.g. 'Mandalay'), free text for report, URL for image. "
                    "For 'orders', 'schedule', 'tasks', 'sysinfo' this is unused "
                    "(live data is fetched by the HUD)."
                )
            )
        }

    def get_required(self) -> List[str]:
        return ["widget_type", "data_payload"]

    async def execute(self, **kwargs) -> str:
        widget_type = kwargs.get("widget_type") or "report"
        data_payload = kwargs.get("data_payload") or ""

        # The streaming brain forwards this JSON verbatim to the browser over /ws/voice.
        return json.dumps({
            "type": "hologram_trigger",
            "action": f"render_{widget_type}",
            "data": data_payload,
        }, ensure_ascii=False)
