import logging
from pydantic import BaseModel, Field
from typing import Type

# ဆရာ့ရဲ့ မူရင်း BaseTool ကို လှမ်းခေါ်ခြင်း
from tools.base import BaseTool

logger = logging.getLogger(__name__)

# ၁။ AI ဆီမှ တောင်းခံမည့် အချက်အလက်များ (Pydantic Schema)
class RecordJammerOrderArgs(BaseModel):
    chat_id: int = Field(..., description="Customer ၏ Chat ID")
    customer_name: str = Field(..., description="Customer ၏ အမည်")
    phone: str = Field(..., description="Customer ၏ ဖုန်းနံပါတ်")
    city: str = Field(..., description="Customer ၏ မြို့")
    address: str = Field(..., description="Customer ၏ လိပ်စာ အပြည့်အစုံ")
    payment_type: str = Field(..., description="ငွေချေစနစ် (ဥပမာ - အိမ်ရောက်ငွေချေ သို့မဟုတ် ငွေကြိုရှင်း)")

# ၂။ Main Tool Class
class RecordJammerOrderTool(BaseTool):
    name = "record_jammer_order"
    description = "Jammer Order အချက်အလက်များကို လက်ခံပြီး ဆရာ့ရဲ့ Saved Messages သို့ ဘောက်ချာပုံစံဖြင့် လှမ်းပို့ပေးမည့် Tool"
    args_schema: Type[BaseModel] = RecordJammerOrderArgs

    async def execute(self, chat_id: int, customer_name: str, phone: str, city: str, address: str, payment_type: str) -> str:
        try:
            # 📦 ဘောက်ချာ သပ်သပ်ရပ်ရပ် ဖန်တီးခြင်း
            order_receipt = (
                "📦 [Jammer Order အသစ် ရပါပြီ]\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 အမည်: {customer_name}\n"
                f"📱 ဖုန်း: {phone}\n"
                f"🏙 မြို့: {city}\n"
                f"💳 ငွေချေစနစ်: {payment_type}\n"
                f"🏠 လိပ်စာ: {address}\n"
                f"💬 Chat ID: {chat_id}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
            # 🌟 Saved Messages သို့ ပို့ခြင်း 
            # (မှတ်ချက် - ဆရာ့ရဲ့ Publisher Bot သို့မဟုတ် Userbot Client ကို ဒီနေရာမှာ လှမ်းခေါ်ပါမည်။ 
            # အောက်ပါ import သည် ဆရာ့ project ၏ လမ်းကြောင်းပေါ်မူတည်၍ အနည်းငယ် ပြင်ရန် လိုနိုင်ပါသည်။)
            from interfaces.telegram_bot import app 
            
            # "me" ဆိုသည်မှာ Telegram ၏ Saved Messages ကို ကိုယ်စားပြုပါသည်
            await app.send_message("me", order_receipt)
            
            logger.info(f"✅ Jammer Order for {customer_name} saved successfully.")
            
            return "Order successfully saved to Sir's Saved Messages."
            
        except Exception as e:
            logger.error(f"❌ Failed to record Jammer order: {e}")
            return f"Failed to record order. Error: {str(e)}"