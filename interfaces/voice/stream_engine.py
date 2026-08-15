import json
import logging
import re
import asyncio
import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import Config
from core.brain import JarvisBrain

logger = logging.getLogger("JARVIS_VOICE_ENGINE")

router = APIRouter()

PING_INTERVAL_SEC = 20

# Burmese neural voice (Microsoft Edge TTS — free, no API key)
EDGE_TTS_VOICE = "my-MM-ThihaNeural"


def is_voice_origin_allowed(origin: str | None) -> bool:
    """Defense-in-depth Origin check. Empty allowlist = allow all (local dev)."""
    allowed = Config.VOICE_ALLOWED_ORIGINS
    if not allowed:
        return True
    if not origin:
        return False
    return origin.rstrip("/") in allowed


@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if not is_voice_origin_allowed(origin):
        logger.warning(f"🚫 Voice WS rejected Origin: {origin!r}")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info(f"🎤 Voice Streaming Connected! (Client: {client_ip})")

    ceo_brain = JarvisBrain(role="ceo", voice_mode=True)
    ping_task = asyncio.create_task(_ping_loop(websocket))
    # Per-connection conversation memory (last 12 turns)
    chat_history = []

    async def fetch_tts(text_chunk, seq_id):
        text_chunk = text_chunk.strip()
        if len(text_chunk) < 1 or not re.search(r'[a-zA-Zက-အ0-9]', text_chunk):
            return seq_id, None, text_chunk

        try:
            communicate = edge_tts.Communicate(text_chunk, EDGE_TTS_VOICE)
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
            msg_type = message.get("type", "")

            # Keepalive from client (reply to our ping, or client-initiated)
            if msg_type in ("pong", "ping"):
                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            user_text = message.get("text", "")

            if user_text:
                logger.info(f"🗣️ User: {user_text}")

                response_stream = ceo_brain.stream_think(user_text, chat_history=chat_history)
                buffer = ""
                reply_parts = []  # for per-connection conversation memory

                # 🚀 Progressive Chunking & Task Queue စနစ်သစ်
                task_queue = asyncio.Queue()
                current_seq_id = 0
                is_first_chunk = True  # ပထမဆုံး စကားစု (First chunk) ဖြစ်ကြောင်း မှတ်သားရန်

                async def sender_worker():
                    """Task များကို တန်းစီထားသည့်အတိုင်း (FIFO) အတိအကျ စောင့်၍ Browser သို့ပို့မည်"""
                    while True:
                        task = await task_queue.get()
                        if task is None:
                            break  # အဆုံးသတ်

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

                    reply_parts.append(chunk)
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
                            is_first_chunk = False  # ပထမတစ်ပိုင်း အမြန်ဖြတ်ပြီးသွားသဖြင့် False သို့ ပြောင်းမည်

                remaining_text = buffer.strip()
                if remaining_text:
                    task = asyncio.create_task(fetch_tts(remaining_text, current_seq_id))
                    await task_queue.put(task)

                # Stream ပြီးဆုံးကြောင်း အသိပေးမည်
                await task_queue.put(None)
                await sender_task  # အကုန်ပို့ပြီးသည်အထိ စောင့်မည်

                # Save this turn so the next turn remembers it (last 12 turns)
                full_reply = "".join(reply_parts).strip()
                if full_reply:
                    chat_history.append(f"Sir: {user_text}\nJarvis: {full_reply}")
                    del chat_history[:-12]

    except WebSocketDisconnect:
        logger.warning("⚠️ Voice session closed.")
    except Exception as e:
        logger.error(f"❌ Voice Stream Error: {e}")
    finally:
        ping_task.cancel()
        try:
            await ping_task
        except asyncio.CancelledError:
            pass


async def _ping_loop(websocket: WebSocket) -> None:
    """Send JSON pings so Cloudflare does not idle-drop the socket (~100s)."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL_SEC)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except Exception:
        return
