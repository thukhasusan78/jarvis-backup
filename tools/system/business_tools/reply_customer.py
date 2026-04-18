import sys
import logging
from tools.base import BaseTool
from google.genai import types
from pyrogram.enums import ParseMode

logger = logging.getLogger("REPLY_TOOL")

class ReplyCustomerTool(BaseTool):
    name = "reply_to_customer"
    description = "Send a Telegram message directly to the customer. Use this ONLY to deliver VPN keys or report exact errors back to the customer."
    owner_role = "secretary" # Secretary သာလျှင် သုံးခွင့်ရှိသည်

    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="The exact Telegram Chat ID of the customer."),
            "message": types.Schema(type=types.Type.STRING, description="The message to send (e.g., the VPN vless:// link).")
        }

    async def execute(self, chat_id: int, message: str) -> str:
        try:
            # မျက်နှာစာမှာ Run နေတဲ့ Pyrogram App ကို လှမ်းယူမည်
            app = sys.modules.get('interfaces.userbot.secretary_main').app
            if app:
                # HTML ParseMode ဖွင့်ပေးလိုက်ခြင်းဖြင့် <code> tags များကို အလုပ်လုပ်စေမည်
                await app.send_message(chat_id, message, parse_mode=ParseMode.HTML)
                return f"✅ Message successfully sent to Chat ID {chat_id}."
            return "❌ Error: Pyrogram App not running in this process."
        except Exception as e:
            logger.error(f"Reply Tool Error: {e}")
            return f"❌ Failed to send message: {e}"