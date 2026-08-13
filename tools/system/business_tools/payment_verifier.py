import logging
import re
import json
from tools.base import BaseTool
from google.genai import types
from perception.vision_analyzer import analyze_image_with_gemini
from memory.business_storage import (
    is_transaction_exists,
    record_transaction,
    get_transaction,
    STATUS_VERIFIED,
    STATUS_FULFILLED,
)
from core.business_catalog import VIP_SUBSCRIPTION_PRICE_MMK

logger = logging.getLogger("PAYMENT_VERIFIER")


class PaymentVerifierTool(BaseTool):
    name = "verify_payment"
    description = (
        "CRITICAL TOOL: Analyzes a payment receipt image, extracts the Transaction ID, "
        "and checks the Business Ledger. On success records status=VERIFIED (not yet FULFILLED). "
        "Pass product='vip' or product='jammer' and the correct min_amount."
    )
    owner_role = "business_manager"

    def get_parameters(self):
        return {
            "image_path": types.Schema(type=types.Type.STRING, description="The file path of the receipt image."),
            "customer_name": types.Schema(type=types.Type.STRING, description="The name of the customer."),
            "min_amount": types.Schema(
                type=types.Type.INTEGER,
                description=f"Minimum acceptable paid amount in MMK. Default {VIP_SUBSCRIPTION_PRICE_MMK} (VIP). "
                            "For jammer prepaid pass full price; for Mandalay deposit pass 10000; 0 skips amount check.",
            ),
            "product": types.Schema(
                type=types.Type.STRING,
                description="Product being paid for: 'vip' or 'jammer'. Default 'vip'.",
            ),
        }

    def get_required(self):
        return ["image_path"]

    async def execute(
        self,
        image_path: str,
        customer_name: str = "Telegram Customer",
        min_amount: int = VIP_SUBSCRIPTION_PRICE_MMK,
        product: str = "vip",
    ) -> str:
        logger.info(f"🔍 [ANTI-FRAUD] Verifying {product} payment receipt for {customer_name}...")

        import datetime
        from config import Config

        current_time = datetime.datetime.now(Config.TIMEZONE)
        time_str = current_time.strftime("%Y-%m-%d %I:%M %p")
        product = (product or "vip").strip().lower()
        if product not in {"vip", "jammer"}:
            logger.warning("Unknown payment product %r; defaulting to vip", product)
            product = "vip"

        prompt = f"""
        The current date and time is {time_str}.
        Extract the following details from this payment receipt:
        1. 'transaction_id' (လုပ်ငန်းစဉ်အမှတ်)
        2. 'amount' (transfer amount)
        3. 'recipient_name' (ငွေလက်ခံသူ၏ အမည်)
        4. 'transfer_time' (the exact date and time shown on the receipt)

        Compare the 'transfer_time' on the receipt with the current time ({time_str}). If the receipt is older than 2 hours from the current time, set "is_within_2_hours": false. Otherwise, set it to true.

        Reply strictly in JSON format like this:
        {{"transaction_id": "1234567890", "amount": "5000", "recipient_name": "Thu Kha Su San", "is_within_2_hours": true}}
        If you cannot find a valid transaction ID, reply with {{"error": "No ID found"}}.
        """

        try:
            ai_response = await analyze_image_with_gemini(image_path, prompt)

            # Non-greedy JSON extraction
            json_str = re.search(r'\{.*?\}', ai_response, re.DOTALL)
            if not json_str:
                return f"❌ Verification Failed: ပုံဝါးနေသဖြင့် ဖတ်၍မရပါ။ AI output: {ai_response}"

            data = json.loads(json_str.group())

            if "error" in data:
                return "❌ Verification Failed: ပြေစာပေါ်တွင် လုပ်ငန်းစဉ်အမှတ် (Transaction ID) ရှာမတွေ့ပါ။ ပြေစာအစစ် မဟုတ်နိုင်ပါ။"

            txn_id = str(data.get("transaction_id", "")).strip()
            amount = str(data.get("amount", "")).strip()
            recipient_name = str(data.get("recipient_name", "")).strip().lower()
            is_within_2_hours = data.get("is_within_2_hours", True)

            amount_digits = re.sub(r"\D", "", amount)
            paid_amount = int(amount_digits) if amount_digits else 0
            if min_amount > 0 and paid_amount < min_amount:
                return (
                    f"❌ Verification Failed: ငွေပမာဏ မလုံလောက်ပါ။ "
                    f"အနည်းဆုံး {min_amount:,} MMK ဖြစ်ရပါမည်။ (လွှဲထားငွေ: {paid_amount:,} MMK)"
                )

            if len(txn_id) < 6:
                return f"❌ Verification Failed: လုပ်ငန်းစဉ်အမှတ် ({txn_id}) မှာ တိုလွန်းနေသဖြင့် အတုဖြစ်နိုင်ပါသည်။"

            if not is_within_2_hours:
                return "❌ Verification Failed: ငွေလွှဲပြေစာမှာ ၂ နာရီထက် ကျော်လွန်နေပါသည်။ လတ်တလော လွှဲထားသော ပြေစာကိုသာ လက်ခံပါမည်။"

            if "thu kha su san" not in recipient_name and "သုခစုစံ" not in recipient_name:
                return (
                    f"❌ Verification Failed: ငွေလက်ခံသူအမည် မှားယွင်းနေပါသည်။ "
                    f"(လက်ခံသူ: {recipient_name}) ဆရာ Thu Kha Su San ထံသို့ လွှဲထားသော ပြေစာသာ ဖြစ်ရပါမည်။"
                )

            existing = get_transaction(txn_id)
            if existing:
                status = existing.get("status")
                if status == STATUS_FULFILLED:
                    return (
                        f"🚫 [FRAUD ALERT]: လုပ်ငန်းစဉ်အမှတ် {txn_id} သည် အရင်က သုံးပြီးသား ပြေစာအဟောင်း ဖြစ်နေပါသည်။ "
                        "ချက်ချင်း ငြင်းပယ်ပြီး Customer ထံသို့ အသိပေးပါ။ (DO NOT generate an invite link!)"
                    )
                if status == STATUS_VERIFIED:
                    # Allow re-fulfillment after a previous verify that never fulfilled
                    return (
                        f"✅ SUCCESS: ပြေစာအမှတ် {txn_id} ({amount} MMK) သည် VERIFIED ဖြစ်ပြီးသား — "
                        f"FULFILLMENT ကို ဆက်လုပ်နိုင်ပါသည်။ product={product} txn_id={txn_id}"
                    )
                return (
                    f"🚫 [FRAUD ALERT]: လုပ်ငန်းစဉ်အမှတ် {txn_id} သည် status={status} ဖြစ်နေပါသည်။ ငြင်းပယ်ပါ။"
                )

            inserted = record_transaction(txn_id, amount, customer_name, STATUS_VERIFIED, product=product)
            if not inserted:
                # Race: another worker inserted between get and insert
                return (
                    f"🚫 [FRAUD ALERT]: လုပ်ငန်းစဉ်အမှတ် {txn_id} သည် အရင်က သုံးပြီးသား ပြေစာအဟောင်း ဖြစ်နေပါသည်။ "
                    "ချက်ချင်း ငြင်းပယ်ပြီး Customer ထံသို့ အသိပေးပါ။"
                )

            next_step = (
                "VIP channel invite link ထုတ်ပေးနိုင်ပါသည်။"
                if product == "vip"
                else "Jammer order ကို record_jammer_order ဖြင့် ဆက်မှတ်နိုင်ပါသည်။"
            )
            return (
                f"✅ SUCCESS: ပြေစာအမှတ် {txn_id} ({amount} MMK) မှာ အသစ်ဖြစ်ပြီး မှန်ကန်ပါသည် (status=VERIFIED). "
                f"product={product} txn_id={txn_id}. {next_step}"
            )

        except Exception as e:
            logger.error(f"Payment Verifier Error: {e}")
            return f"❌ System Error during verification: {str(e)}"
