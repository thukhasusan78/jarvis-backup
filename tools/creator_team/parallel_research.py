import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
import html2text
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from config import Config

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

logger = logging.getLogger("JARVIS_PARALLEL_RESEARCH")

class ParallelResearchTool(BaseTool):
    """
    The Perplexity Engine: Searches the web and scrapes multiple URLs SIMULTANEOUSLY.
    """
    name = "parallel_deep_search"
    description = "Perform a deep, parallel internet search. It searches Tavily and reads up to 5 websites SIMULTANEOUSLY. Always use this instead of standard search when doing deep research."
    owner_role = "deep_researcher"

    def __init__(self):
        if hasattr(Config, 'TAVILY_KEY') and Config.TAVILY_KEY:
            self.tavily = TavilyClient(api_key=Config.TAVILY_KEY)
        else:
            self.tavily = None

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "query": types.Schema(
                type=types.Type.STRING, 
                description="The search query (e.g., 'DeepSeek AI tech specs', 'DeepSeek site:reddit.com')"
            )
        }

    def get_required(self) -> List[str]:
        return ["query"]

    async def fetch_page(self, client, url):
        """Website တစ်ခုချင်းစီကို ဝင်ဖတ်မယ့် Async Function"""
        try:
            # Browser လို ဟန်ဆောင်ပြီး ဝင်မည်
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = await client.get(url, headers=headers, timeout=15.0, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose() # အမှိုက်တွေ ရှင်းထုတ်မည်
                
            converter = html2text.HTML2Text()
            converter.ignore_images = True
            text = converter.handle(str(soup))
            
            # စာမျက်နှာတစ်ခုကို စာလုံးရေ ၅၀၀၀ ထိပဲ ယူမည် (Token သက်သာစေရန်)
            return f"\n\n--- 🌐 EXTRACTED FROM: {url} ---\n{text[:5000]}"
        except Exception as e:
            return f"\n\n--- 🌐 EXTRACTED FROM: {url} ---\n[Failed to scrape content: {str(e)}]"

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not self.tavily: return "Error: Tavily API Key missing."

        logger.info(f"⚡ Parallel Searching for: {query}")
        try:
            # 1. Tavily ဖြင့် Search အရင်လုပ်မည်
            search_result = self.tavily.search(query=query, search_depth="advanced", max_results=5)
            urls = [res['url'] for res in search_result.get('results', [])]
            
            if not urls:
                return "No URLs found for this query."

            # 2. ထွက်လာတဲ့ Link ၅ ခုလုံးကို ပြိုင်တူ (Parallel) ဝင်ဖတ်မည်
            async with httpx.AsyncClient(verify=False) as client:
                tasks = [self.fetch_page(client, url) for url in urls]
                pages_content = await asyncio.gather(*tasks)

            # 3. အချက်အလက်အားလုံးကို ပေါင်းပြီး AI ဆီ တစ်ခါတည်း ပြန်ပို့မည်
            final_report = f"🔍 [PARALLEL SEARCH RESULTS FOR: '{query}']\n"
            final_report += "".join(pages_content)
            
            # Gemini Context Limit မပြည့်အောင် ဖြတ်ထုတ်မည်
            return final_report[:35000] 
        except Exception as e:
            logger.error(f"Parallel Search Error: {e}")
            return f"Parallel Search Error: {str(e)}"