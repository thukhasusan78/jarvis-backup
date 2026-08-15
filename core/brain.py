import os
import json
import time
import logging
from google.genai import types
from config import Config
from core.registry import tool_registry
from core.prompts.context_manager import context_manager
from core.gemini_client import build_client, is_quota_error

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_BRAIN")

# Voice HUD sessions talk directly to Sir — delegation/Telegram reporting only
# delays the answer and sends it to the wrong channel.
VOICE_HUD_DIRECTIVE = """
[VOICE HUD MODE — HIGHEST PRIORITY]
- You are on a LIVE voice call with Sir right now. Answer in short, natural spoken Burmese (1-3 sentences unless he asks for detail). No markdown, no bullet lists.
- NEVER use delegate_task or report_to_sir — those report to Telegram and he will never hear the answer here.
- For news or web questions, call search_web yourself, then summarize the results out loud.
- When Sir asks to SEE something, call show_hologram (map / weather / orders / schedule / tasks / sysinfo / report / image) and also give a one-line spoken summary.
"""

class JarvisBrain:
    # Voice sessions answer directly — delegation/report tools only send the
    # answer to Telegram, so they are removed from the voice tool belt.
    VOICE_BLOCKED_TOOLS = {"delegate_task", "report_to_sir", "publish_event"}

    def __init__(self, role: str = "ceo", voice_mode: bool = False):
        """
        Jarvis Brain Initialization with Dynamic Model Routing
        """
        self.role = role
        self.voice_mode = voice_mode
        self.model_name = Config.MODEL_NAME  # Default အနေနဲ့ Normal Model ကို အရင်ပေးထားမယ်
        
        # ၁။ Agent ရဲ့ ကိုယ်ပိုင်ဖိုင်ကို prompts folder အောက်မှာ နေရာအနှံ့လိုက်ရှာမယ်
        base_prompt_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        prompt_path = None
        
        for root, dirs, files in os.walk(base_prompt_dir):
            if f'{self.role}.md' in files:
                prompt_path = os.path.join(root, f'{self.role}.md')
                break
                
        system_prompt_path = os.path.join(base_prompt_dir, 'system.md')
        
        # ကိုယ်ပိုင်ဖိုင်ရှိရင် အဲဒါဖတ်မယ်၊ မရှိရင် system.md ကို ဖတ်မယ်
        prompt_path = prompt_path if prompt_path else system_prompt_path

        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.system_instruction = f.read()

            # 💡 SMART ROUTER LOGIC: (မူလအတိုင်း ထားရှိသည်)
            if "[MODEL: SMART]" in self.system_instruction:
                self.model_name = Config.SMART_MODEL_NAME
        else:
            self.system_instruction = "You are a helpful AI assistant."

        # Registry ကနေ Role နဲ့ ကိုက်ညီတာကိုပဲ အလိုလို ခွဲယူမယ်
        declarations = tool_registry.get_declarations_for_role(self.role)
        if self.voice_mode:
            declarations = [d for d in declarations if d.name not in self.VOICE_BLOCKED_TOOLS]
        self.tools_config = [
            types.Tool(
                function_declarations=declarations
            )
        ]

    def _get_client(self):
        """Round-Robin Key Rotation Client"""
        return build_client()

    def think(self, user_input, chat_history=[], context_memory=""):
        """
        The Main Thinking Process with Automatic Retry & Key Rotation
        """
        max_retries = 5  # Key 5 ခုရှိလို့ ၅ ခါ retry မယ်
        attempt = 0

        while attempt < max_retries:
            try:
                client = self._get_client()
                
                # ပွဲစား (Context Manager) ဆီကနေ အချိန်နဲ့ မှတ်ဉာဏ်တွေကို ယူမယ်
                dynamic_context = context_manager.get_current_context()

                # Context ပေါင်းစပ်ခြင်း
                full_prompt = f"""
                {dynamic_context}
                
                Context from Memory:
                {context_memory}
                
                Chat History:
                {chat_history}
                
                User Input:
                {user_input}
                """

                # Gemini 2.5 Call
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        tools=self.tools_config,
                        temperature=0.7, # Creative but focused
                    )
                )
                
                return response

            except Exception as e:
                logger.error(f"API Error with key attempt {attempt+1}: {e}")
                
                # 429 means Rate Limit - Rotate Key immediately
                if is_quota_error(e):
                    logger.warning("Rate Limit hit! Rotating to next API Key...")
                    attempt += 1
                    time.sleep(1) # ခဏစောင့်ပြီး နောက် Key ပြောင်း
                else:
                    # တခြား Error ဆိုရင်လည်း Retry မယ် (Network error ဖြစ်နိုင်လို့)
                    logger.warning(f"Unexpected error. Rotating key just in case. Error: {e}")
                    attempt += 1
                    time.sleep(2)

        return "Error: All API Keys failed. Please check your quota or connection."

    async def stream_think(self, user_input, chat_history=[], context_memory=""):
            """
            Voice WebSocket အတွက် အသံချက်ချင်းထုတ်နိုင်ရန် True Streaming
            (Tools များနှင့် Context များကို အပြည့်အဝ အသုံးပြုနိုင်သည်)

            Tool Feedback Loop ပါဝင်သည် — Tool Result ကို Model ဆီ ပြန်ပို့၍
            Spoken Answer ကို ဆက်လက် Stream လုပ်သည် (delegate/Telegram report မလိုအပ်)။
            """
            try:
                # 1. Client နှင့် အချက်အလက်များ ပြင်ဆင်ခြင်း
                client = self._get_client()
                dynamic_context = context_manager.get_current_context()

                full_prompt = f"""
                {dynamic_context}

                {VOICE_HUD_DIRECTIVE}

                Context from Memory:
                {context_memory}

                Chat History:
                {chat_history}

                User Input:
                {user_input}
                """

                # 2. Config သတ်မှတ်ခြင်း (Tools များ ပါဝင်သည်)
                config = types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=self.tools_config,
                    temperature=0.7,
                )

                # 3. 🤖 Async Stream + Tool Feedback Loop (အများဆုံး ၃ ပတ်ခန့်)
                contents = [full_prompt]

                for _round in range(3):
                    response_stream = await client.aio.models.generate_content_stream(
                        model=self.model_name,
                        contents=contents,
                        config=config
                    )

                    fn_calls = []
                    model_parts = []

                    async for chunk in response_stream:
                        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                            model_parts.extend(chunk.candidates[0].content.parts)

                        if chunk.function_calls:
                            fn_calls.extend(chunk.function_calls)

                        # --- ပုံမှန် စာသားများကို ချက်ချင်း Yield ---
                        if chunk.text:
                            yield chunk.text

                    # Tool call မပါရင် Spoken Answer ပြီးပါပြီ
                    if not fn_calls:
                        return

                    # Model ရဲ့ function_call parts များကို history ထဲ ထည့်မည်
                    if model_parts:
                        contents.append(types.Content(role="model", parts=model_parts))

                    # 4. ⚙️ Tool များကို Run ပြီး Results ကို Model ဆီ ပြန်ပို့မည်
                    response_parts = []
                    for fc in fn_calls:
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}
                        logger.info(f"⚙️ Streaming Brain executing tool: {tool_name}")

                        tool_result = await tool_registry.execute_tool(
                            tool_name, caller_role=self.role, **tool_args
                        )

                        # show_hologram ကဲ့သို့ UI-bound tool များ၏ JSON ကို browser သို့ verbatim yield မည်
                        if isinstance(tool_result, str) and '"hologram_trigger"' in tool_result:
                            yield tool_result.strip()
                        else:
                            yield json.dumps({
                                "type": "hologram_trigger",
                                "action": "render_tool",
                                "data": f"{tool_name} executed",
                            })

                        response_parts.append(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": str(tool_result)[:4000]},
                            )
                        )

                    contents.append(types.Content(role="user", parts=response_parts))

            except Exception as e:
                logger.error(f"❌ Streaming Error: {e}")
                yield "တောင်းပန်ပါတယ် ဆရာ၊ အင်တာနက် ချိတ်ဆက်မှု အဆင်မပြေဖြစ်နေပါတယ်။"