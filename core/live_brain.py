import os
import asyncio
import logging
from google import genai
from google.genai import types
from config import Config

# 🧠 (PHASE 3) လိုအပ်သော Tools များနှင့် Context များကို လှမ်းခေါ်ခြင်း
from core.registry import tool_registry
from core.prompts.context_manager import context_manager

logger = logging.getLogger("JARVIS_LIVE_BRAIN")

class LiveBrain:
    def __init__(self, websocket):
        self.ws = websocket  
        self.api_key = Config.get_next_api_key()
        self.client = genai.Client(api_key=self.api_key)
        
        self.model = getattr(Config, "VOICE_MODEL", "gemini-2.5-flash")
        self.voice_name = getattr(Config, "VOICE_NAME", "Aoede")
        
        # 1. Persona ဖတ်ယူခြင်း
        self.base_instruction = self._load_persona("ceo")

    def _load_persona(self, role: str) -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', f'{role}.md')
        system_path = os.path.join(os.path.dirname(__file__), 'prompts', 'system.md')
        target_path = prompt_path if os.path.exists(prompt_path) else system_path
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are JARVIS, an advanced AI assistant."

    async def run_session(self):
        max_retries = 5  
        
        # 2. 🧠 (PHASE 3) လက်ရှိ အချိန်နှင့် User မှတ်ဉာဏ်များကို System Instruction ထဲသို့ ပေါင်းထည့်ခြင်း
        dynamic_context = context_manager.get_current_context()
        full_instruction = f"{dynamic_context}\n\n{self.base_instruction}"
        
        # 3. 🛠️ (PHASE 3) CEO သုံးခွင့်ရှိသော Tools များကို Registry မှ လှမ်းဆွဲခြင်း
        tools_declarations = tool_registry.get_declarations_for_role("ceo")
        live_tools = [types.Tool(function_declarations=tools_declarations)] if tools_declarations else None

        for attempt in range(max_retries):
            try:
                logger.info(f"🎙️ Connecting to Gemini Live API ({self.model})... (Attempt {attempt + 1})")
                
                config = types.LiveConnectConfig(
                    response_modalities=[types.LiveModality.AUDIO],
                    system_instruction=types.Content(parts=[types.Part.from_text(text=full_instruction)]),
                    tools=[
                        types.Tool(function_declarations=tools_declarations),
                        {"google_search": {}} # Native Google Search Grounding ကို ဖွင့်လိုက်ပါပြီ
                    ],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name
                            )
                        )
                    )
                )

                async with self.client.aio.live.connect(model=self.model, config=config) as session:
                    logger.info("✅ Connected to Gemini Live API successfully. (Tools & Context Armed)")
                    
                    send_task = asyncio.create_task(self._receive_from_browser_send_to_gemini(session))
                    recv_task = asyncio.create_task(self._receive_from_gemini_send_to_browser(session))
                    
                    await asyncio.gather(send_task, recv_task)
                    return 
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Gemini Live API Error: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  
                    await asyncio.sleep(wait_time)
                else:
                    raise e

    async def _receive_from_browser_send_to_gemini(self, session):
        try:
            while True:
                data = await self.ws.receive_bytes()
                await session.send(input={"data": data, "mime_type": "audio/pcm"}, end_of_turn=False)
        except Exception as e:
            logger.warning(f"Browser input stream stopped: {e}")

    async def _receive_from_gemini_send_to_browser(self, session):
        try:
            async for response in session.receive():
                # --- (က) အသံ (Audio) များကို လက်ခံပြီး Browser သို့ ပို့ခြင်း ---
                server_content = response.server_content
                if server_content is not None:
                    model_turn = server_content.model_turn
                    if model_turn is not None:
                        for part in model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                await self.ws.send_bytes(part.inline_data.data)
                
                # --- (ခ) 🛠️ (PHASE 3) Tool Call များကို ဖမ်းယူ၍ အလုပ်လုပ်ခြင်း ---
                tool_call = response.tool_call
                if tool_call is not None:
                    for fc in tool_call.function_calls:
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}
                        
                        logger.info(f"⚙️ Live Brain executing tool: {tool_name} with args: {tool_args}")
                        
                        # Registry မှတစ်ဆင့် Tool ကို အမှန်တကယ် Run မည်
                        tool_result = await tool_registry.execute_tool(tool_name, **tool_args)
                        
                        # ရလာသော အဖြေ (Result) ကို Gemini ဆီသို့ ချက်ချင်း ပြန်ပို့ပေးမည် (Function Response)
                        await session.send(
                            input=types.LiveClientContent(
                                client_content=types.Content(
                                    parts=[types.Part.from_function_response(
                                        name=tool_name,
                                        response={"result": str(tool_result)}
                                    )]
                                )
                            )
                        )
                        logger.info(f"✅ Tool '{tool_name}' result sent back to Gemini.")
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error receiving from Gemini: {e}")
            raise e