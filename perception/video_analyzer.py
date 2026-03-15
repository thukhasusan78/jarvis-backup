import asyncio
import logging
from google import genai
from google.genai import types
from config import Config

logger = logging.getLogger("JARVIS_VIDEO_ANALYZER")

def _normalize_youtube_url(url: str) -> str:
    """Gemini AI တိုက်ရိုက်ဖတ်နိုင်ရန် Shorts နှင့် youtu.be လင့်ခ်များကို Standard Form သို့ ပြောင်းပေးမည်"""
    video_id = None
    if "shorts/" in url:
        video_id = url.split("shorts/")[1].split("?")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    elif "watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]
        
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

def _run_video_analysis(original_url: str, prompt: str) -> str:
    locked_api_key = Config.get_next_api_key()
    client = genai.Client(api_key=locked_api_key)
    
    # 🔥 FIX: Perplexity ၏ လမ်းညွှန်ချက်အတိုင်း Native Support ပါသော SMART_MODEL ကို ပြောင်းသုံးမည်
    model_name = getattr(Config, 'SMART_MODEL_NAME', 'gemini-2.5-pro')

    url = _normalize_youtube_url(original_url)
    logger.info(f"🚀 Using Native Gemini YouTube Integration for: {url}")
    
    try:
        logger.info("🧠 Sending YouTube URL directly to Gemini Backend...")
        
        # 🔥 THE NATIVE WAY: yt-dlp များ လုံးဝမလိုတော့ဘဲ YouTube URL ကို file_uri အနေဖြင့် တိုက်ရိုက်ခွံ့ကျွေးခြင်း
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_uri(
                    file_uri=url,
                    mime_type="video/mp4" # YouTube လင့်ခ်ဖြစ်သော်လည်း MP4 အနေဖြင့် ကြေညာပေးရမည်
                )
            ]
        )
        
        return f"✨ **[Analysis via Native YouTube Integration]**\n\n{response.text}"

    except Exception as e:
        logger.error(f"Native Video Analysis Error: {e}")
        return f"❌ Failed to analyze video directly: {str(e)}"

def analyze_video_url(url: str, prompt: str):
    """Async loop ထဲတွင် run ရန်"""
    # ဤနေရာတွင် async def အစား asyncio.run သို့မဟုတ် thread ဖြင့် run ရန် လိုအပ်ပါက သုံးနိုင်သည်
    # ယခင် code ပုံစံအတိုင်း to_thread ဖြင့် ပြန်လည် ပေးပို့ပါမည်
    pass

async def analyze_video_url(url: str, prompt: str) -> str:
    return await asyncio.to_thread(_run_video_analysis, url, prompt)