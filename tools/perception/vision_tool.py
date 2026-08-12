from tools.base import BaseTool
from perception.vision_analyzer import analyze_image_with_gemini

class VisionTool(BaseTool):
    name = "analyze_image"
    owner_role = ["ceo"]
    
    # 🔥 FIX: AI ကို "ဘယ်သူလဲမေးရင် Local AI ကိုပဲ ယုံ၊ Tool မသုံးနဲ့" လို့ အတိအကျ ညွှန်ကြားခြင်း
    description = """
    USE THIS TOOL ONLY WHEN the user explicitly asks for details ABOUT the image (e.g., "what am I doing?", "read this text", "what is in the background?").
    
    🛑 CRITICAL RULE 1: If the user simply asks "Who is this?" or "Is this me?" or "ဒါဘယ်သူလဲ", DO NOT USE THIS TOOL. Look at the [Local Face Analysis] result in your system memory and answer directly based on that. Only call this tool if you need to explain background objects, actions, or text.
    
    🛑 CRITICAL RULE 2: DO NOT delegate this task to 'web_surfer'. Execute it yourself!
    
    Args:
    - image_path (str): The exact file path of the image.
    - prompt (str): The specific question or instruction about the image.
    """

    async def execute(self, image_path: str, prompt: str = "ဒီပုံထဲမှာ ဘာတွေပါလဲ၊ အသေးစိတ် ရှင်းပြပေးပါ။") -> str:
        try:
            result = await analyze_image_with_gemini(image_path, prompt)
            return result
        except Exception as e:
            return f"❌ Vision Tool Error: {str(e)}"