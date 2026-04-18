import logging
import re
import json
from tools.base import BaseTool
from google.genai import types
from perception.vision_analyzer import analyze_image_with_gemini
from memory.business_storage import is_transaction_exists, record_transaction

logger = logging.getLogger("PAYMENT_VERIFIER")

class PaymentVerifierTool(BaseTool):
    name = "verify_payment"
    description = "CRITICAL TOOL: Analyzes a payment receipt image, extracts the Transaction ID, and checks the Business Ledger to prevent fake or duplicate receipts."
    owner_role = "business_manager" # Business Manager သာလျှင် သုံးခွင့်ရှိသည်

    def get_parameters(self):
        return {
            "image_path": types.Schema(type=types.Type.STRING, description="The file path of the receipt image."),
            "customer_name": types.Schema(type=types.Type.STRING, description="The name of the customer.")
        }

    async def execute(self, image_path: str, customer_name: str) -> str:
        logger.info(f"🔍 [ANTI-FRAUD] Verifying payment receipt for {customer_name}...")
        
        import datetime
        from config import Config
        current_time = datetime.datetime.now(Config.TIMEZONE)
        # AI ကို ၂ နာရီ တွက်ချက်ရ လွယ်အောင် အချိန်အတိအကျ (နာရီ၊ မိနစ်) ကိုပါ ထည့်ပေးလိုက်မည်
        time_str = current_time.strftime("%Y-%m-%d %I:%M %p")

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
            # မျက်စိဖြင့် စစ်ဆေးခြင်း
            ai_response = await analyze_image_with_gemini(image_path, prompt)
            
            # JSON Data အဖြစ် သန့်စင်ခြင်း
            json_str = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_str:
                return f"❌ Verification Failed: ပုံဝါးနေသဖြင့် ဖတ်၍မရပါ။ AI output: {ai_response}"
                
            data = json.loads(json_str.group())
            
            if "error" in data:
                return "❌ Verification Failed: ပြေစာပေါ်တွင် လုပ်ငန်းစဉ်အမှတ် (Transaction ID) ရှာမတွေ့ပါ။ ပြေစာအစစ် မဟုတ်နိုင်ပါ။"
                
            txn_id = str(data.get("transaction_id", "")).strip()
            amount = str(data.get("amount", "")).strip()
            recipient_name = str(data.get("recipient_name", "")).strip().lower()
            is_within_2_hours = data.get("is_within_2_hours", True)
            
            if len(txn_id) < 6:
                return f"❌ Verification Failed: လုပ်ငန်းစဉ်အမှတ် ({txn_id}) မှာ တိုလွန်းနေသဖြင့် အတုဖြစ်နိုင်ပါသည်။"

            # --- 🕒 အချိန် (၂) နာရီအတွင်း ဟုတ်/မဟုတ် စစ်ဆေးခြင်း ---
            if not is_within_2_hours:
                return "❌ Verification Failed: ငွေလွှဲပြေစာမှာ ၂ နာရီထက် ကျော်လွန်နေပါသည်။ လတ်တလော လွှဲထားသော ပြေစာကိုသာ လက်ခံပါမည်။"

            # --- 👤 ငွေလက်ခံသူ အမည် စစ်ဆေးခြင်း ---
            # KPay တွင် 'U Thu Kha Su San' ဟု ပေါ်တတ်သဖြင့် အမည်ပါဝင်မှု (Contains) ကိုသာ စစ်ဆေးမည်
            if "thu kha su san" not in recipient_name and "သုခစုစံ" not in recipient_name:
                return f"❌ Verification Failed: ငွေလက်ခံသူအမည် မှားယွင်းနေပါသည်။ (လက်ခံသူ: {recipient_name}) ဆရာ Thu Kha Su San ထံသို့ လွှဲထားသော ပြေစာသာ ဖြစ်ရပါမည်။"

            # ၂။ Database ထဲတွင် သွားရောက်တိုက်စစ်ခြင်း (The Iron Logic)
            if is_transaction_exists(txn_id):
                return f"🚫 [FRAUD ALERT]: လုပ်ငန်းစဉ်အမှတ် {txn_id} သည် အရင်က သုံးပြီးသား ပြေစာအဟောင်း ဖြစ်နေပါသည်။ ချက်ချင်း ငြင်းပယ်ပြီး Customer ထံသို့ အသိပေးပါ။ (DO NOT generate a key!)"
                
            # ၃။ အသစ်ဖြစ်နေပါက Ledger ထဲတွင် မှတ်တမ်းတင်ထားမည်
            record_transaction(txn_id, amount, customer_name, "VERIFIED")
            
            return f"✅ SUCCESS: ပြေစာအမှတ် {txn_id} ({amount} MMK) မှာ အသစ်ဖြစ်ပြီး မှန်ကန်ပါသည်။ VPN Key ဆက်လက် ထုတ်ပေးနိုင်ပါသည်။"

        except Exception as e:
            logger.error(f"Payment Verifier Error: {e}")
            return f"❌ System Error during verification: {str(e)}"