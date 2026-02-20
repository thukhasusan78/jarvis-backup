import os
import base64
import logging
from typing import Dict, List
from google.genai import types, Client

from tools.base import BaseTool
from tools.browser.session import BrowserManager
from config import Config

logger = logging.getLogger("JARVIS_VISUAL")

class VisualTool(BaseTool):
    """
    Visual Debugging and Captcha Solver Tool.
    Takes a screenshot of the current browser page and uses AI Vision to analyze it.
    """
    name = "browser_visual"
    description = "Take a screenshot of the current browser page and analyze it using AI vision. Use this to bypass simple captchas, read hidden text, or debug UI errors when the HTML reading tool fails."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["analyze_screen", "solve_captcha"],
                description="'analyze_screen' to read the general UI or errors, 'solve_captcha' to specifically extract text from a captcha image."
            ),
            "prompt": types.Schema(
                type=types.Type.STRING,
                description="Specific question about the screen (e.g., 'What does the red error message say?', 'Extract the alphanumeric text from the captcha image')."
            )
        }

    def get_required(self) -> List[str]:
        return ["action", "prompt"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        prompt = kwargs.get("prompt")
        screenshot_path = os.path.abspath(os.path.join("workspace", "current_screen.png"))

        try:
            context = await BrowserManager.get_browser_context()
            pages = context.pages
            if not pages:
                return "Error: No browser page is currently open."
            page = pages[0]

            os.makedirs("workspace", exist_ok=True)

            # မျက်နှာပြင်ကို Screenshot ရိုက်ယူခြင်း
            await page.screenshot(path=screenshot_path, full_page=False)

            # ရိုက်ယူထားသော ပုံကို Base64 အဖြစ် ပြောင်းလဲခြင်း
            with open(screenshot_path, "rb") as image_file:
                image_data = image_file.read()

            # Gemini API အား ခေါ်ယူ၍ ပုံကို ဖတ်ခိုင်းခြင်း
            client = Client(api_key=Config.get_next_api_key())
            
            vision_prompt = f"Analyze this screenshot. {prompt}"
            if action == "solve_captcha":
                vision_prompt = f"This is a captcha image. You must strictly return ONLY the solution (the text characters to type). Do not add any extra conversational text or formatting. {prompt}"

            response = client.models.generate_content(
                model=Config.MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type='image/png'),
                    vision_prompt
                ]
            )

            # နေရာမယူစေရန် Screenshot ဖိုင်ကို ချက်ချင်း ပြန်ဖျက်ခြင်း
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)

            return f"Vision Analysis Result:\n{response.text}"

        except Exception as e:
            logger.error(f"Visual Tool Error: {e}")
            return f"Failed to analyze screen visually: {str(e)}"