import logging
import os
import asyncio
from google.genai import types
from config import Config
from core.registry import tool_registry
from memory.memory_controller import memory_controller

from core.gemini_client import build_client, is_quota_error

logger = logging.getLogger("SECRETARY_BRAIN")

class SecretaryBrain:
    def __init__(self):
        # 🌟 ပြင်ဆင်ချက်: Key ကို အသေမမှတ်တော့ဘဲ Request လာမှ လှမ်းခေါ်သုံးမည်
        self.model_name = Config.MODEL_NAME
        
        # --- DYNAMIC PROMPT FINDER ---
        base_prompt_dir = os.path.join(os.getcwd(), 'core', 'prompts')
        self.system_instruction = "You are Jarvis, an AI Secretary." 
        
        # Prompt ဖိုင်ကို တိုက်ရိုက် လမ်းကြောင်းပေးပြီး ဖတ်မည်
        prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'business','secretary.md')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.system_instruction = f.read()
                logger.info(f"✅ SUCCESS: Secretary Prompt ကို အောင်မြင်စွာ ဖတ်ယူနိုင်ပါပြီ။")
        except Exception as e:
            logger.error(f"❌ Error reading prompt: {e}")
        
        # --- NEW: SECRETARY အတွက် TOOL များ တပ်ဆင်ခြင်း ---
        self.tools_config = [
            types.Tool(function_declarations=tool_registry.get_declarations_for_role("secretary"))
        ]

    def _get_client(self):
        return build_client()

    async def reply(self, chat_id: int, user_name: str, text: str, chat_history_text: str) -> str:
        """Async Background Delegation ပါဝင်သော Chat System"""
        import datetime
        current_time = datetime.datetime.now(Config.TIMEZONE)
        time_str = current_time.strftime("%Y-%m-%d %I:%M %p")
        
        # --- NEW: RAG Retrieval from ChromaDB ---
        rag_context = ""
        try:
            # Customer မေးတဲ့စာ (text) နဲ့ ကိုက်ညီတဲ့ အချက်အလက်တွေကို Database ထဲကနေ ဆွဲထုတ်မယ်
            rag_facts = memory_controller.search_business_facts(text, limit=Config.CHROMA_TOP_K)
            if rag_facts:
                rag_context = f"\n\n[ LIVE BUSINESS KNOWLEDGE (Prioritize this over static instructions) ]\n{rag_facts}"
        except Exception as e:
            logger.warning(f"⚠️ RAG Retrieval Error: {e}")

        # 🚀 AI ကို Chat ID, အချိန် နှင့် RAG Data ပါ ထည့်ပေးလိုက်ခြင်း
        full_prompt = f"SYSTEM NOTE: The current Customer's Chat ID is {chat_id}. Current Myanmar Time is {time_str}.{rag_context}\n\nChat History:\n{chat_history_text}\n\nUser ({user_name}): {text}"
        
        # 🌟 ပြင်ဆင်ချက်: Main Brain အတိုင်း Key Rotation နှင့် Auto-Retry စနစ် ထည့်သွင်းခြင်း
        max_retries = 5
        attempt = 0

        while attempt < max_retries:
            try:
                # Request တစ်ခေါက်လာတိုင်း Key အသစ်တစ်ချောင်းကို အလှည့်ကျ ဆွဲယူမည်
                client = self._get_client()
                
                # 🔄 MULTI-STEP TOOL LOOP: Tool ရလဒ်တွေကို Model ဆီ ပြန်ပေးပြီး ဆက်လုပ်စေမည်
                # (ဥပမာ - ပုံ ၂ ပုံ ဆက်တိုက်ပို့ခြင်း)။ Infinite Loop ကာကွယ်ရန် အများဆုံး ၃ ရှော့သာ ခွင့်ပြုမည်။
                contents = full_prompt
                MAX_TOOL_ITERATIONS = 3

                for iteration in range(MAX_TOOL_ITERATIONS):
                    response = await client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_instruction,
                            temperature=0.7,
                            tools=self.tools_config
                        )
                    )

                    # Tool မခေါ်တော့ဘဲ Text အဖြေထွက်လာရင် ချက်ချင်း ပြန်ပေးမည်
                    if not response.function_calls:
                        return response.text if response.text else "..."

                    # Tool (များ) အလုပ်လုပ်ပြီး ရလဒ်များ စုစည်းမည်
                    tool_results_text = ""
                    for fc in response.function_calls:
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}

                        # Business events must never ask the customer for a name we
                        # already have from Telegram. Models can omit optional tool
                        # arguments, so inject deterministic request context here.
                        if tool_name == "publish_event":
                            event_type = str(tool_args.get("event_type", ""))
                            if event_type in {
                                "VERIFY_AND_FULFILL_SUBSCRIPTION",
                                "VERIFY_AND_FULFILL_JAMMER",
                                "RECORD_JAMMER_ORDER",
                            }:
                                tool_args.setdefault("chat_id", chat_id)
                                tool_args.setdefault(
                                    "customer_name",
                                    user_name or f"Telegram Customer {chat_id}",
                                )

                        logger.info(f"⚙️ Secretary triggering tool: {tool_name} with args: {tool_args}")

                        tool_result = await tool_registry.execute_tool(
                            tool_name, caller_role="secretary", **tool_args
                        )
                        tool_results_text += f"[Tool '{tool_name}' Result]: {tool_result}\n"

                    # ရလဒ်များကို ပေါင်းထည့်ပြီး နောက်တစ်ချက် ဆက်တွေးခိုင်းမည်
                    contents = (
                        f"{contents}\n\n{tool_results_text}\n"
                        "Based on the tool result(s) above, continue: either call the NEXT needed tool to finish the customer's request, "
                        "or reply to the customer naturally in short polite Burmese. "
                        "If a background process was started (e.g. publish_event), tell the customer to wait a moment. "
                        "If an action completed (e.g. photo sent), confirm it warmly."
                    )
                    logger.info(f"🔄 Tool loop iteration {iteration + 1}/{MAX_TOOL_ITERATIONS} completed.")

                # ၃ ရှော့မျှ လုပ်ပြီးလည်း မပြီးသေးရင် (ရှားပါး) — Fail-safe အဖြေ
                logger.warning("⚠️ Secretary tool loop hit max iterations. Returning fail-safe reply.")
                return "ဟုတ်ကဲ့.. အချက်အလက်များကို လက်ခံရရှိပါပြီခင်ဗျာ။ ခဏလေး စောင့်ပေးပါနော်။"
                
            except Exception as e:
                logger.error(f"❌ Secretary API Error (Attempt {attempt+1}): {str(e)}")
                # 429 ဆိုသည်မှာ Quota ပြည့်သွားခြင်းဖြစ်သည်။ ချက်ချင်း နောက် Key ကို ပြောင်းမည်။
                if is_quota_error(e):
                    logger.warning("⚠️ Rate Limit hit in Secretary! Rotating to next API Key...")
                    attempt += 1
                    await asyncio.sleep(1) 
                else:
                    logger.warning("⚠️ Unexpected error in Secretary. Retrying...")
                    attempt += 1
                    await asyncio.sleep(2)

        return "စနစ်ပိုင်းဆိုင်ရာ အခက်အခဲလေးဖြစ်သွားလို့ ဆရာလိုင်းပေါ်ရောက်လာရင် စာပြန်ပေးပါလိမ့်မယ်ဗျ။"