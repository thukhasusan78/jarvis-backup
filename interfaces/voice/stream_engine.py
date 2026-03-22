import json
import logging
import re
import asyncio
import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.brain import JarvisBrain

logger = logging.getLogger("JARVIS_VOICE_ENGINE")

# 🚀 FastAPI Router တည်ဆောက်ခြင်း (main.py တွင် လွယ်ကူစွာ ချိတ်ဆက်နိုင်ရန်)
router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_ip = websocket.client.host
    logger.info(f"🎤 Voice Streaming Connected! (Client: {client_ip})")

    # CEO Brain ကို တိုက်ရိုက် အသက်သွင်းမည်
    ceo_brain = JarvisBrain(role="ceo")

    async def synthesize_and_send(text_chunk):
        """စာသားများကို အသံပြောင်းပြီး Browser သို့ ချက်ချင်း Stream လွှင့်ပေးမည့် Function"""
        text_chunk = text_chunk.strip()
        
        # ဖတ်စရာ စာသား/ဂဏန်း မပါလျှင် သို့မဟုတ် စာလုံးရေနည်းလွန်းလျှင် ကျော်မည်
        if len(text_chunk) < 1 or not re.search(r'[a-zA-Zက-အ0-9]', text_chunk): 
            return 
        
        logger.info(f"🔊 TTS Output: {text_chunk}")
        try:
            # မြန်မာအသံ (Nilar) ဖြင့် အသံပြောင်းလဲခြင်း
            communicate = edge_tts.Communicate(text_chunk, "my-MM-ThihaNeural")
            async for audio_chunk in communicate.stream():
                if audio_chunk["type"] == "audio":
                    # အသံ Bytes များကို Browser ဆီသို့ ချက်ချင်း ပို့လွှတ်နေပါပြီ
                    await websocket.send_bytes(audio_chunk["data"])
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    try:
        while True:
            # ၁။ Browser STT မှ ပြောင်းပေးလိုက်သော စာသားကို ဖမ်းယူခြင်း
            data = await websocket.receive_text()
            message = json.loads(data)
            user_text = message.get("text", "")

            if user_text:
                logger.info(f"🗣️ User (Voice): {user_text}")

                # ၂။ 🧠 CEO Brain ၏ stream_think ကို လှမ်းခေါ်ခြင်း (Memory နှင့် Tools များ အလုပ်လုပ်မည်)
                response_stream = ceo_brain.stream_think(user_text)

                buffer = ""

                # ၃။ ⚡ TRUE STREAMING LOGIC (အပိုင်းလိုက် ဖြတ်ထုတ်ခြင်း)
                async for chunk in response_stream:
                    # Tool Call များကြောင့် ထွက်လာသော JSON ဖြစ်ပါက အသံမပြောင်းဘဲ Browser သို့ တိုက်ရိုက်ပို့မည်
                    if chunk.strip().startswith("{") and "type" in chunk:
                        await websocket.send_text(chunk.strip())
                        logger.info(f"🧊 Hologram/Tool JSON Sent to Browser.")
                        continue

                    # ပုံမှန် စာသားဖြစ်ပါက Buffer ထဲသို့ ထည့်မည်
                    buffer += chunk
                    
                    # အင်္ဂလိပ် (, . ? !) နှင့် မြန်မာ (၊ ။ \n) များကို စစ်ဆေးခြင်း
                    match = re.search(r'([.?!၊။\n,]+)', buffer)
                    
                    if match:
                        split_idx = match.end()
                        sentence = buffer[:split_idx].strip()
                        buffer = buffer[split_idx:] # မပြီးသေးသော စာသားများကို buffer တွင် ချန်ထားမည်
                        
                        # စာတစ်ကြောင်း (သို့) ကော်မာတစ်ခု ရသည်နှင့် အသံချက်ချင်းထုတ်မည်
                        if sentence:
                            await synthesize_and_send(sentence)

                # ၄။ Stream ပြီးဆုံးသွားချိန် Buffer ထဲတွင် ကျန်နေသေးသော စာများကို ရှင်းလင်း၍ အသံထုတ်ခြင်း
                remaining_text = buffer.strip()
                if remaining_text:
                    await synthesize_and_send(remaining_text)

    except WebSocketDisconnect:
        logger.warning(f"⚠️ Voice session closed cleanly. (Client: {client_ip})")
    except Exception as e:
        logger.error(f"❌ Voice Stream Engine Error: {e}")