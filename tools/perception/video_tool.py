import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from perception.video_analyzer import analyze_video_url

logger = logging.getLogger("JARVIS_VIDEO_TOOL")

class VideoAnalyzerTool(BaseTool):
    """
    YouTube, Facebook, Vimeo အစရှိသော Video Link များကို ဝင်ရောက်နားထောင်ပေးမည့် Tool
    """
    name = "analyze_video"
    owner_role = "ceo" 
    
    description = """
    USE THIS TOOL WHEN the user provides a Video Link (YouTube, Facebook, TikTok, etc.) and asks you to summarize, analyze, or explain the content of the video.
    
    Args:
    - url (str): The full URL of the video provided by the user.
    - prompt (str): The specific question or instruction about the video.
    """

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "url": types.Schema(
                type=types.Type.STRING,
                description="The complete video URL (e.g., https://www.youtube.com/watch?v=...)."
            ),
            "prompt": types.Schema(
                type=types.Type.STRING,
                description="Specific instructions or questions about the video."
            )
        }

    def get_required(self) -> List[str]:
        return ["url", "prompt"]

    async def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        # မေးခွန်း အတိအကျမပါရင် အနှစ်ချုပ်ဖို့ ပုံသေ သတ်မှတ်ထားမည်
        prompt = kwargs.get("prompt", "ဒီ ဗီဒီယိုရဲ့ အဓိက အကြောင်းအရာတွေကို အသေးစိတ် အနှစ်ချုပ်ပေးပါ။")
        
        try:
            result = await analyze_video_url(url, prompt)
            return result
        except Exception as e:
            return f"❌ Video Tool Error: {str(e)}"