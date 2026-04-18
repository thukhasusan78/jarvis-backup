import os
import requests
import asyncio
import logging
import re
import uuid
from tools.base import BaseTool

logger = logging.getLogger("MARZBAN_TOOL")

# .env ထဲက ဆာဗာ အချက်အလက်များကို လှမ်းယူမည်
MARZBAN_URL = os.getenv("MARZBAN_URL", "https://vpn.thukha.online:8443/api")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "thukhaindustries")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "") 

def _generate_key_sync(username: str, data_limit_gb: int) -> str:
    """Marzban API နှင့် တိုက်ရိုက် ချိတ်ဆက်မည့် Sync Function"""
    try:
        # --- Emoji နှင့် အခြားစာသားများ ဖျက်ထုတ်ပြီး သန့်စင်ခြင်း ---
        safe_username = re.sub(r'[^a-zA-Z0-9]', '', username)
        
        # Marzban လိုအပ်ချက်အရ အနည်းဆုံး ၃ လုံးပြည့်အောင် ဖြည့်မည်
        if safe_username and len(safe_username) < 3:
            safe_username = f"{safe_username}_vpn" # "Ko" ဆိုလျှင် "Ko_vpn" ဖြစ်သွားမည်
        elif not safe_username:
            safe_username = f"user_{uuid.uuid4().hex[:4]}" # မြန်မာစာသီးသန့် (သို့) Emoji သီးသန့် ဖြစ်နေလျှင်
            
        logger.info(f"Sanitized Username: {safe_username}")

        # အဆင့် (၁): Admin Token လှမ်းတောင်းခြင်း
        token_data = {
            "grant_type": "password",
            "username": MARZBAN_USERNAME,
            "password": MARZBAN_PASSWORD
        }
        
        # Network Error တက်လျှင် အလွယ်တကူ သိနိုင်ရန် Timeout ထည့်ထားသည်
        token_res = requests.post(f"{MARZBAN_URL}/admin/token", data=token_data, timeout=10)
        
        if token_res.status_code != 200:
            return f"❌ Token Error: ဆာဗာသို့ လော့ဂ်အင်ဝင်၍မရပါ။ HTTP {token_res.status_code} - {token_res.text}"
            
        # 🚀 THE FIX: JSON မဟုတ်တဲ့စာတွေ ဝင်လာရင် ဖမ်းမည့်စနစ်
        try:
            access_token = token_res.json().get("access_token")
        except Exception:
            return f"❌ Token JSON Error: ဆာဗာမှ ပြန်ပို့သောစာမှာ JSON မဟုတ်ပါ။ တကယ့်စာသား: {token_res.text}"
        
        # အဆင့် (၂): User အသစ်ဖန်တီးခြင်း
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        data_limit_bytes = int(data_limit_gb) * 1073741824
        
        # 🚀 THE FIX: Protocol ရော၊ အပေါက် (Inbound Tag) ကိုပါ အတိအကျ တွဲပေးလိုက်ခြင်း
        payload = {
            "username": safe_username,
            "data_limit": data_limit_bytes,
            "status": "active",
            "proxies": {
                "vless": {}
            },
            "inbounds": {
                "vless": [
                    "VLESS TCP REALITY"
                ]
            }
        }
        
        user_res = requests.post(f"{MARZBAN_URL}/user", headers=headers, json=payload, timeout=10)
        
        if user_res.status_code != 200:
            try:
                error_detail = user_res.json().get('detail', 'Unknown Error')
                return f"❌ User Creation Error: {error_detail}"
            except Exception:
                return f"❌ User API Error: HTTP {user_res.status_code} - {user_res.text}"
            
        user_data = user_res.json()
        links = user_data.get("links", [])
        
        if not links:
            # တကယ်လို့ ထပ်ပြီး လင့်ခ်မထွက်လာရင် တကယ့်ပြဿနာကို မြင်ရအောင် Raw Data ကိုပါ ထုတ်ပေးမည်
            return f"❌ Error: အကောင့်ဖန်တီးပြီးသော်လည်း လင့်ခ် ထွက်မလာပါ။ Raw Data: {user_data}"
            
        return f"✅ SUCCESS: \n{links[0]}"
        
    except requests.exceptions.RequestException as e:
        return f"❌ Network Request Error (ဆာဗာလိပ်စာ မှားနေနိုင်ပါသည်): {str(e)}"
    except Exception as e:
        logger.error(f"Marzban API Error: {str(e)}")
        return f"❌ API Connection Error: {str(e)}"

class MarzbanTool(BaseTool):
    name = "generate_vpn_key"
    owner_role = "vpn_worker" 
    
    description = """
    USE THIS TOOL ONLY to generate a new VPN key for a verified customer.
    
    Args:
    - username (str): The customer's desired username.
    - data_limit_gb (int): Data limit in Gigabytes (e.g., 100).
    """

    async def execute(self, username: str, data_limit_gb: int) -> str:
        logger.info(f"🔑 Generating VPN Key for user: {username} ({data_limit_gb} GB)")
        result = await asyncio.to_thread(_generate_key_sync, username, data_limit_gb)
        return result