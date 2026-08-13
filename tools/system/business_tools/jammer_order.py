import logging
from google.genai import types

from tools.base import BaseTool
from telegram import Bot
from config import Config
from memory.memory_controller import memory_controller
from memory.business_storage import record_jammer_order_row, mark_fulfilled

logger = logging.getLogger(__name__)


class RecordJammerOrderTool(BaseTool):
    name = "record_jammer_order"
    description = (
        "Persist a jammer order and send the Boss a receipt. "
        "ONLY business_manager may call this (after Secretary publishes RECORD_JAMMER_ORDER)."
    )
    owner_role = "business_manager"

    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="Customer ၏ Chat ID"),
            "jammer_model": types.Schema(
                type=types.Type.STRING,
                description="Customer မှာယူသော Jammer Model (ဥပမာ - '2 Antenna' သို့မဟုတ် '3 Antenna')",
            ),
            "customer_name": types.Schema(type=types.Type.STRING, description="Customer ၏ အမည်"),
            "phone": types.Schema(type=types.Type.STRING, description="Customer ၏ ဖုန်းနံပါတ်"),
            "city": types.Schema(type=types.Type.STRING, description="Customer ၏ မြို့"),
            "address": types.Schema(type=types.Type.STRING, description="Customer ၏ လိပ်စာ အပြည့်အစုံ"),
            "payment_type": types.Schema(
                type=types.Type.STRING,
                description="ငွေချေစနစ် (အိမ်ရောက်ငွေချေ/COD သို့မဟုတ် ငွေကြိုရှင်း/Prepaid)",
            ),
            "payment_txn_id": types.Schema(
                type=types.Type.STRING,
                description="Optional verified payment transaction id (prepaid/deposit).",
            ),
        }

    def get_required(self):
        return ["chat_id", "jammer_model", "customer_name", "phone", "city", "address", "payment_type"]

    async def execute(
        self,
        chat_id: int,
        jammer_model: str,
        customer_name: str,
        phone: str,
        city: str,
        address: str,
        payment_type: str,
        payment_txn_id: str = "",
    ) -> str:
        try:
            order_id = record_jammer_order_row(
                chat_id=chat_id,
                jammer_model=jammer_model,
                customer_name=customer_name,
                phone=phone,
                city=city,
                address=address,
                payment_type=payment_type,
                payment_txn_id=payment_txn_id or "",
                status="RECORDED",
            )

            if payment_txn_id:
                mark_fulfilled(payment_txn_id)

            order_receipt = (
                "📦 <b>New Jammer Order Received!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Order #: {order_id}\n"
                f"📡 Model: {jammer_model}\n"
                f"👤 အမည်: {customer_name}\n"
                f"📱 ဖုန်း: {phone}\n"
                f"🏙 မြို့: {city}\n"
                f"💳 ငွေချေစနစ်: {payment_type}\n"
                f"🏠 လိပ်စာ: {address}\n"
                f"💬 Customer: <a href=\"tg://user?id={chat_id}\">{chat_id}</a>\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )

            bot = Bot(token=Config.TELEGRAM_TOKEN)
            await bot.send_message(chat_id=Config.ALLOWED_USER_ID, text=order_receipt, parse_mode="HTML")
            memory_controller.add_chat_message(Config.ALLOWED_USER_ID, "model", order_receipt)

            logger.info(f"✅ Jammer Order #{order_id} for {customer_name} saved successfully.")
            return f"Order successfully saved to Sir's account. order_id={order_id}"

        except Exception as e:
            logger.error(f"❌ Failed to record Jammer order: {e}")
            return f"Failed to record order. Error: {str(e)}"
