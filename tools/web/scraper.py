import requests
from bs4 import BeautifulSoup
import html2text
import logging
from typing import Dict, List
from google.genai import types

# ဖခင် Class ကို လှမ်းခေါ်မယ် (စနစ်သစ်အတွက်)
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_SCRAPER")

class ScraperTool(BaseTool):
    """
    Fetches a webpage and converts it to clean Markdown text.
    Optimized for LLM reading (saves tokens).
    """
    # brain.py ထဲက Tool နာမည်အတိုင်း တိတိကျကျ ပေးရပါမယ်
    name = "read_page_content"
    description = "Extract and read clean text content from a specific URL. Use this to read news, articles, or documentation efficiently."

    def get_parameters(self) -> Dict[str, types.Schema]:
        """Tool အတွက် လိုအပ်တဲ့ parameters များကို ကြေညာခြင်း"""
        return {
            "url": types.Schema(
                type=types.Type.STRING, 
                description="The full URL of the website to read (e.g., https://example.com)"
            )
        }

    def get_required(self) -> List[str]:
        """မဖြစ်မနေ ထည့်ပေးရမယ့် Parameter"""
        return ["url"]

    async def execute(self, **kwargs) -> str:
        """Agent က Tool ကို လှမ်းခိုင်းရင် တကယ် အလုပ်လုပ်မယ့် နေရာ (မူရင်း Logic များ)"""
        url = kwargs.get("url")
        if not url:
            return "Error: No URL provided."

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            logger.info(f"🌐 Scraping URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status() # Check for 404/500 errors

            # 1. Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # 2. Remove Junk (Ads, Navigation, Scripts) - RAM Saver
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()

            # 3. Convert to Markdown (Clean Text)
            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = True # ပုံတွေ မယူဘူး (Token သက်သာအောင်)
            
            markdown_text = converter.handle(str(soup))
            
            # စာလုံးရေကန့်သတ်မယ် (Gemini Context မပြည့်အောင်)
            if len(markdown_text) > 10000:
                return markdown_text[:10000] + "\n...(Content truncated for brevity)"
            return markdown_text

        except Exception as e:
            logger.error(f"Scraping Error: {e}")
            return f"Failed to read page: {str(e)}"