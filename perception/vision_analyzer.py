import os
import logging
import asyncio
from google import genai
from PIL import Image
from config import Config

logger = logging.getLogger("JARVIS_VISION_ANALYZER")

# Sync function အနေဖြင့် API ကို လှမ်းခေါ်မည်
def _run_vision_api(image_path: str, prompt: str) -> str:
    # config.py မှ သတ်မှတ်ထားသော Key များကို လှည့်သုံးမည်
    client = genai.Client(api_key=Config.get_next_api_key())
    
    # config တွင် VISION_MODEL မရှိပါက ပုံသေ 'gemini-1.5-pro' ကို သုံးမည်
    model_name = getattr(Config, 'MODEL_NAME', 'gemini-2.5-flash')
    
    img = Image.open(image_path)
    
    # SDK အသစ်စနစ်ဖြင့် Generate Content ခေါ်ယူခြင်း
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt, img]
    )
    return response.text

async def analyze_image_with_gemini(image_path: str, prompt: str = "ဒီပုံထဲမှာ ဘာတွေပါလဲ၊ အသေးစိတ် ရှင်းပြပေးပါ။") -> str:
    """
    ပုံထဲက စာသားတွေဖတ်ဖို့ သို့မဟုတ် ရှုခင်း/ပစ္စည်းတွေကို ခွဲခြမ်းစိတ်ဖြာဖို့ Gemini Pro ဆီ ပို့မည့်စနစ်
    """
    if not os.path.exists(image_path):
        return f"❌ Error: ပုံဖိုင်ရှာမတွေ့ပါ ({image_path})။ ယာယီသိမ်းဆည်းထားသော အချိန်ကျော်လွန်သွား၍ ဖြစ်နိုင်ပါသည်။ ပုံကို ပြန်ပို့ပေးပါ။"

    try:
        logger.info(f"🧠 Sending image to Gemini API for deep analysis: {image_path}")
        
        # Main Event Loop မပိတ်သွားစေရန် Thread ခွဲပြီး API ခေါ်မည်
        result = await asyncio.to_thread(_run_vision_api, image_path, prompt)
        return result

    except Exception as e:
        logger.error(f"Gemini Vision Error: {e}")
        return f"⚠️ ပုံကို ခွဲခြမ်းစိတ်ဖြာရာတွင် အခက်အခဲဖြစ်သွားပါသည်။ Error: {str(e)}"