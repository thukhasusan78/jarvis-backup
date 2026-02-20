import os
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger("JARVIS_BROWSER")

class BrowserManager:
    _instance = None
    _context = None
    _playwright = None
    # Login Session များကို သိမ်းဆည်းရန် နေရာသတ်မှတ်ခြင်း
    _user_data_dir = os.path.abspath(os.path.join("memory", "browser_profile"))

    @classmethod
    async def get_browser_context(cls):
        """Singleton Pattern with Persistent Context (Saves Cookies & Login State)"""
        if cls._context is None:
            logger.info("Launching Persistent RAM-Optimized Browser...")
            os.makedirs(cls._user_data_dir, exist_ok=True)
            
            cls._playwright = await async_playwright().start()
            
            # Persistent Context ကို သုံးခြင်းဖြင့် Login ဝင်ပြီးသား အကောင့်များ ပြန်မထွက်သွားတော့ပါ
            cls._context = await cls._playwright.chromium.launch_persistent_context(
                user_data_dir=cls._user_data_dir,
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled" # Bot ဟု မထင်စေရန် ကာကွယ်ခြင်း
                ],
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        return cls._context

    @classmethod
    async def close(cls):
        if cls._context:
            await cls._context.close()
            await cls._playwright.stop()
            cls._context = None
            logger.info("Browser Context Closed.")

# RAM ချွေတာရန် ပုံများ၊ ဗီဒီယိုများကို ပိတ်ထားမည့်စနစ်
async def block_agressive_resources(route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()