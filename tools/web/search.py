import json
import logging
from typing import Dict, List, Any
from google.genai import types

# ဖခင် Class ကို လှမ်းခေါ်မယ်
from tools.base import BaseTool
from config import Config

# Tavily Library
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

logger = logging.getLogger("TOOL_SEARCH")

class WebSearchTool(BaseTool):
    """
    အင်တာနက်ပေါ်က အချက်အလက်တွေကို ရှာဖွေပေးမယ့် Tool (Tavily ကို အသုံးပြုထားသည်)
    """
    name = "search_web"
    description = "Search the internet for real-time information, news, or coding solutions."

    def __init__(self):
        # Tool စခေါ်တာနဲ့ Tavily Key ကို တစ်ခါတည်း ချိတ်ဆက်ထားမယ်
        if hasattr(Config, 'TAVILY_KEY') and Config.TAVILY_KEY:
            self.tavily = TavilyClient(api_key=Config.TAVILY_KEY)
        else:
            self.tavily = None
            logger.warning("⚠️ Tavily API Key missing. Search tool will not work.")

    def get_parameters(self) -> Dict[str, types.Schema]:
        """Brain (Gemini) ကို ဒီ Tool မှာ ဘာတွေထည့်ပေးရမလဲ (Parameters) ရှင်းပြခြင်း"""
        return {
            "query": types.Schema(
                type=types.Type.STRING, 
                description="The search query or question."
            )
        }

    def get_required(self) -> List[str]:
        """မဖြစ်မနေ ထည့်ပေးရမယ့် Parameter"""
        return ["query"]

    async def execute(self, **kwargs) -> str:
        """Agent က Tool ကို လှမ်းခိုင်းရင် တကယ် အလုပ်လုပ်မယ့် နေရာ (Main Action)"""
        query = kwargs.get("query")
        if not query:
            return "Error: Search query is missing."
        
        if not self.tavily:
            return "Error: Tavily Key is missing. Cannot search the web."
            
        try:
            logger.info(f"🔍 Searching Web for: {query}")
            # Tavily ဖြင့် ရှာဖွေခြင်း (include_answer=True ဖြင့် အဖြေတိုကိုပါ ယူမည်)
            results = self.tavily.search(
                query=query, 
                search_depth="advanced", 
                max_results=5,
                include_answer=True 
            )
            # ရလာတဲ့ Result ကို String အဖြစ် ပြောင်းပြီး Agent ဆီ ပြန်ပို့မယ်
            return json.dumps(results)[:8000]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search Error: {str(e)}"