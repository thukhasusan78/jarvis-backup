import logging
from pydantic import BaseModel, Field
from typing import Type

# ဆရာ့ရဲ့ မူရင်း BaseTool ကို လှမ်းခေါ်ခြင်း
from tools.base import BaseTool
# Telegram Bot နှင့် Config ကို လှမ်းခေါ်ခြင်း
from telegram import Bot
from config import Config

logger = logging.getLogger(__name__)

# ၁။ AI ဆီမှ တောင်းခံမည့် အချက်အလက်များ (Pydantic Schema)
class RecordJammerOrderArgs(BaseModel):
    chat_id: int = Field(..., description="Customer ၏ Chat ID")
    customer_name: str = Field(..., description="Customer ၏ အမည်")
    phone: str = Field(..., description="Customer ၏ ဖုန်းနံပါတ်")
    city: str = Field(..., description="Customer ၏ မြို့")
    address: str = Field(..., description="Customer ၏ လိပ်စာ အပြည့်အစုံ")
    payment_type: str = Field(..., description="ငွေချေစနစ် (အိမ်ရောက်ငွေချေ သို့မဟုတ် ငွေကြိုရှင်း)")

# ၂။ Main Tool Class
class RecordJammerOrderTool(BaseTool):
    name = "record_jammer_order"
    description = "Jammer Order အချက်အလက်များကို လက်ခံပြီး ဆရာ့ထံသို့ ဘောက်ချာပို့ပေးမည့် Tool"
    args_schema: Type[BaseModel] = RecordJammerOrderArgs

    # 🌟 THE FIX: **kwargs ဖြင့် AI ပို့သမျှ Data ကို ဖမ်းယူခြင်း
    async def execute(self, **kwargs) -> str:
        try:
            # Data များ ဆွဲထုတ်ခြင်း
            chat_id = kwargs.get("chat_id", "Unknown")
            customer_name = kwargs.get("customer_name", "Unknown")
            phone = kwargs.get("phone", "Unknown")
            city = kwargs.get("city", "Unknown")
            address = kwargs.get("address", "Unknown")
            payment_type = kwargs.get("payment_type", "Unknown")

            # 📦 ဘောက်ချာ သပ်သပ်ရပ်ရပ် ဖန်တီးခြင်း
            order_receipt = (
                "📦 <b>New Jammer Order Received!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 အမည်: {customer_name}\n"
                f"📱 ဖုန်း: {phone}\n"
                f"🏙 မြို့: {city}\n"
                f"💳 ငွေချေစနစ်: {payment_type}\n"
                f"🏠 လိပ်စာ: {address}\n"
                f"💬 Customer Chat ID: <code>{chat_id}</code>\n"
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