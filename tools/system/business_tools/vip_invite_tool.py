import sys
import logging
from tools.base import BaseTool
from google.genai import types
from config import Config

logger = logging.getLogger("VIP_INVITE_TOOL")

class VipInviteTool(BaseTool):
    name = "generate_vip_invite_link"
    description = "Generate a one-time invite link to the VIP channel after a payment has been verified. Pass the customer's name for link labeling."
    owner_role = "business_manager"

    def get_parameters(self):
        return {
            "customer_name": types.Schema(type=types.Type.STRING, description="The name of the customer who paid.")
        }

    async def execute(self, customer_name: str) -> str:
        if Config.VIP_CHANNEL_ID == 0:
            return "❌ Config Error: VIP_CHANNEL_ID is not set in .env — cannot generate invite link."

        try:
            app = sys.modules.get('interfaces.userbot.secretary_main').app
            if not app:
                return "❌ Error: Pyrogram userbot app not running in this process."

            link = await app.create_chat_invite_link(
                Config.VIP_CHANNEL_ID,
                member_limit=1,
                name=f"vip_{customer_name}"
            )
            logger.info(f"🔗 VIP invite link generated for {customer_name}: {link.invite_link}")
            return f"✅ SUCCESS: invite link = {link.invite_link}"
        except Exception as e:
            logger.error(f"VIP Invite Tool Error: {e}")
            return f"❌ Failed to create VIP invite link: {e}"
