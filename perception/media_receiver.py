import os
import asyncio
import logging
from perception.face_engine import face_engine

logger = logging.getLogger("JARVIS_MEDIA_RECEIVER")

async def process_incoming_image(file_path: str, caption: str = "") -> str:
    """
    ပုံ ဝင်လာတိုင်း ဤ Function က လက်ခံမည်။
    Bottleneck မဖြစ်စေရန် CPU-heavy အလုပ်များကို နောက်ကွယ် (Thread) သို့ ပို့မည်။
    """
    logger.info(f"📸 Received new image: {file_path}")
    
    # 🚀 NON-BLOCKING MAGIC: CPU အလုပ်လုပ်နေချိန် အခြား AI စကားပြောတာတွေ ရပ်မသွားအောင် Thread ခွဲထုတ်ခြင်း
    face_result = await asyncio.to_thread(face_engine.analyze_image, file_path)
    
    # ရလာတဲ့ ရလဒ်ကို AI ရဲ့ Context ထဲ ထည့်ပေးဖို့ စာသား ပြန်ထုတ်ပေးမည်
    context_msg = f"[SYSTEM: User uploaded an image. File Path: '{file_path}'. Local AI Vision Analysis: {face_result}]"
    
    if caption:
        context_msg += f"\nUser's Caption/Question: {caption}"
    else:
        context_msg += "\n(User did not provide text. Ask the user what they want you to do with this image.)"
        
    # ယာယီဖိုင်ကို ၂၄ နာရီ (၈၆၄၀၀ စက္ကန့်) နေရင် အလိုလို ဖျက်မယ့် စနစ် 
    asyncio.create_task(_delete_file_later(file_path, delay=86400))
    
    return context_msg

async def _delete_file_later(file_path: str, delay: int):
    """Memory Cleanup"""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"🧹 Cleaned up temp media: {file_path}")
        except Exception:
            pass