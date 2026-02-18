import requests
from bs4 import BeautifulSoup
import html2text
import logging

logger = logging.getLogger("JARVIS_SCRAPER")

def read_url(url: str) -> str:
    """
    Fetches a webpage and converts it to clean Markdown text.
    Optimized for LLM reading (saves tokens).
    """
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
        return markdown_text[:10000] + "\n...(Content truncated for brevity)"

    except Exception as e:
        logger.error(f"Scraping Error: {e}")
        return f"Failed to read page: {str(e)}"