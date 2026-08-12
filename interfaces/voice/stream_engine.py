import json
import logging
import re
import asyncio
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

    async def fetch_tts(text_chunk, seq_id):
        text_chunk = text_chunk.strip()
        if len(text_chunk) < 1 or not re.search(r'[a-zA-Zက-အ0-9]', text_chunk): 
            return seq_id, None, text_chunk
        
        try:
            communicate = edge_tts.Communicate(text_chunk, "my-MM-ThihaNeural")
            full_audio_bytes = b""
            async for audio_chunk in communicate.stream():
                if audio_chunk["type"] == "audio":
                    full_audio_bytes += audio_chunk["data"]
            return seq_id, full_audio_bytes, text_chunk
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return seq_id, None, text_chunk

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            user_text = message.get("text", "")

            if user_text:
                logger.info(f"🗣️ User: {user_text}")

                response_stream = ceo_brain.stream_think(user_text)
                buffer = ""
                
                # 🚀 Progressive Chunking & Task Queue စနစ်သစ်
                task_queue = asyncio.Queue()
                current_seq_id = 0
                is_first_chunk = True # ပထမဆုံး စကားစု (First chunk) ဖြစ်ကြောင်း မှတ်သားရန်
                
                async def sender_worker():
                    """Task များကို တန်းစီထားသည့်အတိုင်း (FIFO) အတိအကျ စောင့်၍ Browser သို့ပို့မည်"""
                    while True:
                        task = await task_queue.get()
                        if task is None: 
                            break # အဆုံးသတ်
                            
                        seq_id, audio_bytes, text = await task
                        # အသံပြောင်းရန် ကျရှုံးသွားပါကလည်း UI တွင် စာပေါ်နေစေရန် Text ကို အရင်ပို့ပါမည်
                        await websocket.send_text(json.dumps({"type": "text_stream", "text": text}))
                        if audio_bytes:
                            await websocket.send_bytes(audio_bytes)
                        task_queue.task_done()

                # ပို့မည့် Worker ကို Background တွင် စတင်ထားမည်
                sender_task = asyncio.create_task(sender_worker())

                async for chunk in response_stream:
                    if chunk.strip().startswith("{") and "type" in chunk:
                        await websocket.send_text(chunk.strip())
                        continue

                    buffer += chunk
                    while True:
                        # 💡 Progressive Chunking: ပထမဆုံးကို ကော်မာ (၊, ,) ဖြင့် အမြန်ဖြတ်၍၊ ကျန်စာများကို ပုဒ်မ (။, .) ဖြင့် ဖြတ်မည်
                        pattern = r'([.?!။၊,\n]+)' if is_first_chunk else r'([.?!။\n]+)'
                        match = re.search(pattern, buffer)
                        
                        if not match:
                            break 
                            
                        split_idx = match.end()
                        sentence = buffer[:split_idx].strip()
                        buffer = buffer[split_idx:] 
                        
                        if sentence:
                            # Task အသစ်ဖန်တီးပြီး Queue ထဲသို့ အစဉ်လိုက် ထည့်မည်
                            task = asyncio.create_task(fetch_tts(sentence, current_seq_id))
                            await task_queue.put(task)
                            current_seq_id += 1
                            is_first_chunk = False # ပထမတစ်ပိုင်း အမြန်ဖြတ်ပြီးသွားသဖြင့် False သို့ ပြောင်းမည်

                remaining_text = buffer.strip()
                if remaining_text:
                    task = asyncio.create_task(fetch_tts(remaining_text, current_seq_id))
                    await task_queue.put(task)

                # Stream ပြီးဆုံးကြောင်း အသိပေးမည်
                await task_queue.put(None)
                await sender_task # အကုန်ပို့ပြီးသည်အထိ စောင့်မည်

    except WebSocketDisconnect:
        logger.warning(f"⚠️ Voice session closed.")
    except Exception as e:
        logger.error(f"❌ Voice Stream Error: {e}")