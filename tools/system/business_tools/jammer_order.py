import logging
from google.genai import types

# ဆရာ့ရဲ့ မူရင်း BaseTool ကို လှမ်းခေါ်ခြင်း
from tools.base import BaseTool
# Telegram Bot နှင့် Config ကို လှမ်းခေါ်ခြင်း
from telegram import Bot
from config import Config

logger = logging.getLogger(__name__)

# Main Tool Class
class RecordJammerOrderTool(BaseTool):
    name = "record_jammer_order"
    description = "Jammer Order အချက်အလက်များကို လက်ခံပြီး ဆရာ့ထံသို့ ဘောက်ချာပို့ပေးမည့် Tool"

    # 🌟 THE FIX: Gemini Schema ကို BaseTool convention (get_parameters/get_required) နဲ့ ကြေညာခြင်း
    # (Pydantic args_schema ကို get_declaration() က မဖတ်ဘူးမို့ parameter မပါတဲ့ Tool ဖြစ်နေခဲ့တယ်)
    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="Customer ၏ Chat ID"),
            "customer_name": types.Schema(type=types.Type.STRING, description="Customer ၏ အမည်"),
            "phone": types.Schema(type=types.Type.STRING, description="Customer ၏ ဖုန်းနံပါတ်"),
            "city": types.Schema(type=types.Type.STRING, description="Customer ၏ မြို့"),
            "address": types.Schema(type=types.Type.STRING, description="Customer ၏ လိပ်စာ အပြည့်အစုံ"),
            "payment_type": types.Schema(type=types.Type.STRING, description="ငွေချေစနစ် (အိမ်ရောက်ငွေချေ/COD သို့မဟုတ် ငွေကြိုရှင်း/Prepaid)")
        }

    def get_required(self):
        return ["chat_id", "customer_name", "phone", "city", "address", "payment_type"]

    async def execute(self, chat_id: int, customer_name: str, phone: str, city: str, address: str, payment_type: str) -> str:
        try:

            # 📦 ဘောက်ချာ သပ်သပ်ရပ်ရပ် ဖန်တီးခြင်း
            order_receipt = (
                "📦 <b>New Jammer Order Received!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 အမည်: {customer_name}\n"
                f"📱 ဖုန်း: {phone}\n"
                f"🏙 မြို့: {city}\n"
                f"💳 ငွေချေစနစ်: {payment_type}\n"
                f"🏠 လိပ်စာ: {address}\n"
                f"💬 Customer: <a href=\"tg://user?id={chat_id}\">{chat_id}</a> (နှိပ်ပြီး Chat တိုက်ရိုက်ဖွင့်နိုင်သည်)\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
            # 🌟 THE FIX: Telegram Bot ကို အသုံးပြု၍ ဆရာ့၏ Account (ALLOWED_USER_ID) သို့ တိုက်ရိုက်ပို့ခြင်း
            bot = Bot(token=Config.TELEGRAM_TOKEN)
            await bot.send_message(chat_id=Config.ALLOWED_USER_ID, text=order_receipt, parse_mode="HTML")
            
            logger.info(f"✅ Jammer Order for {customer_name} saved successfully.")
            return "Order successfully saved to Sir's account."
            
        except Exception as e:
            logger.error(f"❌ Failed to record Jammer order: {e}")
            return f"Failed to record order. Error: {str(e)}"