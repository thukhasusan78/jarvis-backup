import os
import asyncio
import logging
from perception.face_engine import face_engine
from perception.vision_analyzer import analyze_image_with_gemini

logger = logging.getLogger("JARVIS_MEDIA_RECEIVER")

# လုပ်ငန်းသုံး ပုံများအတွက် အဓိကရည်ရွယ်ချက်ပါဝင်သော Default Prompt
VISION_BUSINESS_PROMPT = (
    "ဒီပုံထဲမှာ ဘာတွေပါလဲ အသေးစိတ်ရှင်းပြပါ။ "
    "ငွေလွှဲပြေစာ (receipt) ဖြစ်ရင် transaction ID, amount, recipient name, time ကို ထုတ်ပါ။ "
    "ကုန်ပစ္စည်းပုံ/Error screenshot ဖြစ်ရင် ဘာပြဿနာ/ဘာပစ္စည်းလဲ ဖော်ပြပါ။"
)

async def process_incoming_image(file_path: str, caption: str = "") -> str:
    """
    ပုံ ဝင်လာတိုင်း ဤ Function က လက်ခံမည်။
    Bottleneck မဖြစ်စေရန် CPU-heavy အလုပ်များကို နောက်ကွယ် (Thread) သို့ ပို့မည်။
    """
    logger.info(f"📸 Received new image: {file_path}")

    # 🚀 NON-BLOCKING MAGIC: CPU အလုပ်လုပ်နေချိန် အခြား AI စကားပြောတာတွေ ရပ်မသွားအောင် Thread ခွဲထုတ်ခြင်း
    face_result = await asyncio.to_thread(face_engine.analyze_image, file_path)

    # 🧠 GEMINI DEEP VISION: ပုံထဲပါ အကြောင်းအရာကို AI နားလည်စေရန် ခွဲခြမ်းစိတ်ဖြာခြင်း
    try:
        vision_result = await analyze_image_with_gemini(file_path, VISION_BUSINESS_PROMPT)
        if vision_result.startswith("❌") or vision_result.startswith("⚠️"):
            logger.warning(f"Gemini Vision unavailable for {file_path}: {vision_result}")
            vision_result = "unavailable"
    except Exception as e:
        logger.error(f"Gemini Vision failed for {file_path}: {e}")
        vision_result = "unavailable"

    # ရလာတဲ့ ရလဒ်ကိုများ AI ရဲ့ Context ထဲ ထည့်ပေးဖို့ စာသား ပြန်ထုတ်ပေးမည်
    context_msg = (
        f"[SYSTEM: User uploaded an image. File Path: '{file_path}'.\n"
        f"Local Face Analysis: {face_result}\n"
        f"Gemini Vision Analysis: {vision_result}]"
    )

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