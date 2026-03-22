import json
import logging
import re
import asyncio
import time
import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.brain import JarvisBrain

logger = logging.getLogger("JARVIS_VOICE_ENGINE")

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_ip = websocket.client.host
    logger.info(f"🎤 Voice Streaming Connected! (Client: {client_ip})")

    ceo_brain = JarvisBrain(role="ceo")

    async def synthesize_and_send(text_chunk):
        text_chunk = text_chunk.strip()
        if len(text_chunk) < 1 or not re.search(r'[a-zA-Zက-အ0-9]', text_chunk): 
            return 
        
        # --- 🕒 DEBUG LOGGING (START) ---
        start_tts_time = time.time()
        logger.info(f"⏳ [TTS စတင်ချိတ်ဆက်ခြင်း] စာသား: '{text_chunk}'")
        
        try:
            communicate = edge_tts.Communicate(text_chunk, "my-MM-ThihaNeural")
            full_audio_bytes = b""
            first_byte_time = None
            
            async for audio_chunk in communicate.stream():
                if audio_chunk["type"] == "audio":
                    if not first_byte_time:
                        first_byte_time = time.time()
                        logger.info(f"⚡ [TTS ပထမဆုံးအသံရရှိမှု] ကြာချိန်: {first_byte_time - start_tts_time:.3f} စက္ကန့်")
                    full_audio_bytes += audio_chunk["data"]
            
            if full_audio_bytes:
                download_end_time = time.time()
                logger.info(f"✅ [TTS အပြီးသတ်ရရှိမှု] စုစုပေါင်းကြာချိန်: {download_end_time - start_tts_time:.3f} စက္ကန့်")
                
                await websocket.send_text(json.dumps({"type": "text_stream", "text": text_chunk}))
                await websocket.send_bytes(full_audio_bytes)
                logger.info(f"🚀 [Browser သို့ ပို့လွှတ်ပြီးပါပြီ]")
                
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            user_text = message.get("text", "")

            if user_text:
                logger.info(f"🗣️ User (Voice): {user_text}")

                gemini_start = time.time()
                logger.info(f"🧠 [Gemini စတင်စဉ်းစားနေပါပြီ...]")

                response_stream = ceo_brain.stream_think(user_text)
                buffer = ""
                text_queue = asyncio.Queue()

                async def tts_worker():
                    while True:
                        chunk_text = await text_queue.get()
                        if chunk_text is None: 
                            break
                        
                        logger.info(f"👷 [Worker မှ အသံပြောင်းရန် ယူလိုက်ပါပြီ] စာသား: '{chunk_text}'")
                        await synthesize_and_send(chunk_text)
                        text_queue.task_done()

                worker_task = asyncio.create_task(tts_worker())

                async for chunk in response_stream:
                    if chunk.strip().startswith("{") and "type" in chunk:
                        await websocket.send_text(chunk.strip())
                        continue

                    buffer += chunk
                    match = re.search(r'([.?!၊။\n,]+)', buffer)
                    
                    if match:
                        split_idx = match.end()
                        sentence = buffer[:split_idx].strip()
                        buffer = buffer[split_idx:] 
                        
                        if sentence:
                            logger.info(f"📥 [Gemini စာထုတ်ပေးမှု] '{sentence}' (ကြာချိန်: {time.time() - gemini_start:.3f} စက္ကန့်)")
                            await text_queue.put(sentence)

                remaining_text = buffer.strip()
                if remaining_text:
                    await text_queue.put(remaining_text)

                await text_queue.put(None)
                await worker_task 

    except WebSocketDisconnect:
        logger.warning(f"⚠️ Voice session closed cleanly. (Client: {client_ip})")
    except Exception as e:
        logger.error(f"❌ Voice Stream Engine Error: {e}")