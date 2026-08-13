import logging
from tools.base import BaseTool
from google.genai import types
from config import Config
from interfaces.customer_messaging import customer_messaging
from memory.business_storage import mark_fulfilled

logger = logging.getLogger("VIP_INVITE_TOOL")


class VipInviteTool(BaseTool):
    name = "generate_vip_invite_link"
    description = (
        "Generate a one-time invite link to the VIP channel after a payment has been verified. "
        "Pass customer_name and optional payment_txn_id to mark the ledger FULFILLED on success."
    )
    owner_role = "business_manager"

    def get_parameters(self):
        return {
            "customer_name": types.Schema(type=types.Type.STRING, description="The name of the customer who paid."),
            "payment_txn_id": types.Schema(
                type=types.Type.STRING,
                description="Verified transaction id from verify_payment — marked FULFILLED after link creation.",
            ),
        }

    def get_required(self):
        return []

    async def execute(
        self,
        customer_name: str = "VIP Customer",
        payment_txn_id: str = "",
    ) -> str:
        if Config.VIP_CHANNEL_ID == 0:
            return "❌ Config Error: VIP_CHANNEL_ID is not set in .env — cannot generate invite link."

        try:
            link = await customer_messaging.create_chat_invite_link(
                Config.VIP_CHANNEL_ID,
                member_limit=1,
                name=f"vip_{customer_name}",
            )
            if payment_txn_id:
                mark_fulfilled(payment_txn_id)
            logger.info(f"🔗 VIP invite link generated for {customer_name}: {link.invite_link}")
            return f"✅ SUCCESS: invite link = {link.invite_link}"
        except Exception as e:
            logger.error(f"VIP Invite Tool Error: {e}")
            return (
                "❌ Failed to create VIP invite link: "
                f"{e}. Protected-content settings do not block invite creation; "
                "check the channel ID, userbot membership, and admin invite rights."
            )
