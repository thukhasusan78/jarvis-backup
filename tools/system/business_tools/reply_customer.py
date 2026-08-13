import logging
from tools.base import BaseTool
from google.genai import types
from pyrogram.enums import ParseMode
from interfaces.customer_messaging import customer_messaging

logger = logging.getLogger("REPLY_TOOL")


class ReplyCustomerTool(BaseTool):
    name = "reply_to_customer"
    description = (
        "Send a Telegram message directly to the customer. "
        "Use this to deliver VIP invite links or report exact errors back to the customer."
    )
    owner_role = ["business_manager", "secretary"]

    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="The exact Telegram Chat ID of the customer."),
            "message": types.Schema(
                type=types.Type.STRING,
                description="The message to send (e.g., the VIP invite link wrapped in <code> tags).",
            ),
        }

    async def execute(self, chat_id: int, message: str) -> str:
        try:
            await customer_messaging.send_message(chat_id, message, parse_mode=ParseMode.HTML)
            return f"✅ Message successfully sent to Chat ID {chat_id}."
        except Exception as e:
            logger.error(f"Reply Tool Error: {e}")
            return f"❌ Failed to send message: {e}"
