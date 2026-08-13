import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from core.movie_engine import trigger_manual_movie

logger = logging.getLogger(__name__)


class ManualMovieTriggerTool(BaseTool):
    name = "manual_movie_trigger"
    description = (
        "Laptop ဖွင့်စရာမလိုဘဲ Telegram မှတစ်ဆင့် Channel ID နှင့် Message ID ကိုပေး၍ "
        "ဇာတ်ကားကို Manual တင်ခိုင်းမည့် Tool"
    )
    owner_role = "ceo"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "channel_id": types.Schema(
                type=types.Type.STRING,
                description="Target Channel ၏ ID (ဥပမာ: '-1001234567')",
            ),
            "message_id": types.Schema(
                type=types.Type.STRING,
                description="Target Message ၏ ID (ဥပမာ: '456')",
            ),
        }

    def get_required(self) -> List[str]:
        return ["channel_id", "message_id"]

    async def execute(self, **kwargs) -> str:
        try:
            logger.info(f"🔧 Manual Movie Trigger Received Args: {kwargs}")

            channel_id_raw = kwargs.get("channel_id")
            message_id_raw = kwargs.get("message_id")

            if not channel_id_raw or not message_id_raw:
                return "❌ Tool ကို ခေါ်ရာတွင် `channel_id` နှင့် `message_id` ကို Argument အနေဖြင့် အတိအကျ ထည့်ပေးရန် လိုအပ်ပါသည်။"

            channel_id = int(str(channel_id_raw).strip())
            message_id = int(str(message_id_raw).strip())

            logger.info(f"🚀 Triggering Manual Movie: Channel {channel_id}, Message {message_id}")
            return await trigger_manual_movie(channel_id, message_id)

        except ValueError:
            return "❌ Channel ID နှင့် Message ID များသည် ဂဏန်းများသာ ဖြစ်ရပါမည်။"
        except Exception as e:
            logger.error(f"❌ Manual Movie Trigger Error: {e}")
            return f"❌ ဇာတ်ကားတင်ရန် အခက်အခဲဖြစ်နေပါသည်။ Error: {str(e)}"
