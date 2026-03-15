import os
import logging
import google.generativeai as genai
from PIL import Image
from config import Config

logger = logging.getLogger("JARVIS_VISION_ANALYZER")

# Gemini API ကို ချိတ်ဆက်ခြင်း (config.py ထဲက API Key ကို ဆွဲယူမည်)
if hasattr(Config, 'GEMINI_API_KEY') and Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)
else:
    logger.warning("⚠️ GEMINI_API_KEY ရှာမတွေ့ပါ။ config.py တွင် ထည့်သွင်းထားရန် လိုအပ်ပါသည်။")

async def analyze_image_with_gemini(image_path: str, prompt: str = "ဒီပုံထဲမှာ ဘာတွေပါလဲ၊ အသေးစိတ် ရှင်းပြပေးပါ။") -> str:
    """
    ပုံထဲက စာသားတွေဖတ်ဖို့ သို့မဟုတ် ရှုခင်း/ပစ္စည်းတွေကို ခွဲခြမ်းစိတ်ဖြာဖို့ Gemini Pro ဆီ ပို့မည့်စနစ်
    """
    if not os.path.exists(image_path):
        return f"❌ Error: ပုံဖိုင်ရှာမတွေ့ပါ ({image_path})။ ယာယီသိမ်းဆည်းထားသော အချိန် (၅ မိနစ်) ကျော်လွန်သွား၍ ဖျက်ပစ်လိုက်ပြီ ဖြစ်နိုင်ပါသည်။ ပုံကို ပြန်ပို့ပေးပါ။"

    try:
        logger.info(f"🧠 Sending image to Gemini API for deep analysis: {image_path}")
        img = Image.open(image_path)
        
        # 🚀 Hardcode အစား Config ကနေ လှမ်းခေါ်ခြင်း (မရှိရင် default အနေနဲ့ pro ကို သုံးမည်)
        model_name = getattr(Config, 'MODEL_NAME', 'gemini-2.5-flash')
        model = genai.GenerativeModel(model_name)
        
        response = await model.generate_content_async([prompt, img])
        return response.text

    except Exception as e:
        logger.error(f"Gemini Vision Error: {e}")
        return f"⚠️ ပုံကို ခွဲခြမ်းစိတ်ဖြာရာတွင် အခက်အခဲဖြစ်သွားပါသည်။ Error: {str(e)}"