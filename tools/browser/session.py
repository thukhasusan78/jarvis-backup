from playwright.async_api import async_playwright
import logging

logger = logging.getLogger("JARVIS_BROWSER")

class BrowserManager:
    _instance = None
    _browser = None
    _playwright = None

    @classmethod
    async def get_browser(cls):
        """Singleton Pattern: Browser တစ်ခုတည်းကိုပဲ ဖွင့်ပြီး ပြန်သုံးမယ်"""
        if cls._browser is None:
            logger.info("🦊 Launching RAM-Optimized Browser...")
            cls._playwright = await async_playwright().start()
            
            # RAM Saving Flags for Linux VPS
            cls._browser = await cls._playwright.chromium.launch(
                headless=True, # မျက်နှာပြင် မပေါ်စေရ
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage", # Shared memory error မတက်အောင်
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu"
                ]
            )
        return cls._browser

    @classmethod
    async def close(cls):
        if cls._browser:
            await cls._browser.close()
            await cls._playwright.stop()
            cls._browser = None
            logger.info("💤 Browser Closed.")

# Helper to block images (Network Logic)
async def block_agressive_resources(route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()