import os
import logging
import json
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

        # --- 🍪 AGGRESSIVE COOKIE INJECTION (FORCE INJECT EVERY TIME) ---
        # Browser ရှိပြီးသားဖြစ်နေရင်တောင် Cookie ကို အတင်းပြန်ထည့်မည်
        cookie_path = os.path.abspath(os.path.join("memory", "facebook_cookies.json"))
        if os.path.exists(cookie_path):
            try:
                with open(cookie_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    
                    for cookie in cookies:
                        if "sameSite" in cookie:
                            if cookie["sameSite"] is None:
                                del cookie["sameSite"]
                            else:
                                val = str(cookie["sameSite"]).lower()
                                if val in ["strict", "lax", "none"]:
                                    cookie["sameSite"] = val.capitalize() 
                                elif val == "no_restriction":
                                    cookie["sameSite"] = "None"
                                else:
                                    del cookie["sameSite"]  
                        
                        for key in ["hostOnly", "session", "storeId"]:
                            cookie.pop(key, None)

                    await cls._context.add_cookies(cookies)
                    # Log တွေ အရမ်းရှုပ်မနေအောင် ဖြုတ်ထားလိုက်သည်
                    # logger.info("🍪 Secure Facebook Cookies injected aggressively!")
            except Exception as e:
                logger.error(f"Failed to load cookies: {e}")
        # -----------------------------------------

        return cls._context

    @classmethod
    async def close_browser(cls):
        """အလုပ်လုပ်ပြီးပါက Browser ကို ပြန်ပိတ်ပြီး RAM ကို ရှင်းလင်းမည်"""
        if cls._context:
            await cls._context.close()
            cls._context = None
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
        logging.getLogger("JARVIS_BROWSER").info("🧹 Browser ပိတ်ပြီး RAM ကို အောင်မြင်စွာ ရှင်းလင်းလိုက်ပါပြီ။")    

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