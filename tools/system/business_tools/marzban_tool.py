import os
import requests
import asyncio
import logging
from tools.base import BaseTool
import re
import uuid

logger = logging.getLogger("MARZBAN_TOOL")

# .env ထဲက ဆာဗာ အချက်အလက်များကို လှမ်းယူမည်
MARZBAN_URL = os.getenv("MARZBAN_URL", "https://vpn.thukha.online:8443/api")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "thukhaindustries")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "") # .env တွင် သေချာထည့်ပေးရန်

def _generate_key_sync(username: str, data_limit_gb: int) -> str:
    """Marzban API နှင့် တိုက်ရိုက် ချိတ်ဆက်မည့် Sync Function"""
    try:
        # --- NEW: Emoji နှင့် အခြားစာသားများ ဖျက်ထုတ်ပြီး သန့်စင်ခြင်း ---
        safe_username = re.sub(r'[^a-zA-Z0-9]', '', username)
        
        # နာမည်က Emoji တွေချည်းပဲဖြစ်နေလို့ ဖျက်လိုက်တဲ့အခါ ဘာမှမကျန်တော့ရင် ကျပန်းနာမည် ပေးမည်
        if not safe_username or len(safe_username) < 3:
            safe_username = f"user_{uuid.uuid4().hex[:6]}"
            
        logger.info(f"Sanitized Username: {safe_username}")
        # အဆင့် (၁): Admin Token လှမ်းတောင်းခြင်း
        token_data = {
            "grant_type": "password",
            "username": MARZBAN_USERNAME,
            "password": MARZBAN_PASSWORD
        }
        token_res = requests.post(f"{MARZBAN_URL}/admin/token", data=token_data, timeout=10)
        
        if token_res.status_code != 200:
            return f"❌ Token Error: ဆာဗာသို့ လော့ဂ်အင်ဝင်၍မရပါ။ ({token_res.text})"
            
        access_token = token_res.json().get("access_token")
        
        # အဆင့် (၂): User အသစ်ဖန်တီးခြင်း
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # GB ကို Bytes သို့ ပြောင်းခြင်း (1 GB = 1073741824 Bytes)
        data_limit_bytes = int(data_limit_gb) * 1073741824
        
        payload = {
            "username": safe_username,
            "data_limit": data_limit_bytes
            # Proxies များကို မထည့်သွင်းပါက Panel တွင် Default သတ်မှတ်ထားသော VLESS Reality ကိုသာ Auto ယူပါမည်။
        }
        
        user_res = requests.post(f"{MARZBAN_URL}/user", headers=headers, json=payload, timeout=10)
        
        # User ရှိပြီးသားဖြစ်နေလျှင် (သို့) Error တက်လျှင်
        if user_res.status_code != 200:
            return f"❌ User Creation Error: {user_res.json().get('detail', 'Unknown Error')}"
            
        user_data = user_res.json()
        links = user_data.get("links", [])
        
        if not links:
            return "❌ Error: အကောင့်ဖန်တီးပြီးသော်လည်း vless:// လင့်ခ် ထွက်မလာပါ။"
            
        # VLESS link ကို ပြန်ပို့ပေးမည် (ပထမဆုံး လင့်ခ်ကိုသာ ယူမည်)
        return f"✅ SUCCESS: \n{links[0]}"
        
    except Exception as e:
        logger.error(f"Marzban API Error: {str(e)}")
        return f"❌ API Connection Error: {str(e)}"

class MarzbanTool(BaseTool):
    name = "generate_vpn_key"
    owner_role = "vpn_worker" 
    
    description = """
    USE THIS TOOL ONLY to generate a new VPN key for a verified customer.
    
    Args:
    - username (str): The customer's desired username (e.g., 'thukha01'). MUST be English letters and numbers only. No spaces.
    - data_limit_gb (int): Data limit in Gigabytes (e.g., 100).
    """

    async def execute(self, username: str, data_limit_gb: int) -> str:
        logger.info(f"🔑 Generating VPN Key for user: {username} ({data_limit_gb} GB)")
        # Main Event Loop မရပ်သွားစေရန် Async/Thread ဖြင့် ခေါ်ယူမည်
        result = await asyncio.to_thread(_generate_key_sync, username, data_limit_gb)
        return result