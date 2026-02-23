import os
import time
import subprocess
import socket
import logging
from datetime import datetime
import requests
from config import Config 

# Logger သတ်မှတ်ခြင်း
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WATCHDOG] - %(message)s')
logger = logging.getLogger("Supervisor")

def send_alert(message):
    """CEO ထံသို့ Telegram မှတစ်ဆင့် အရေးပေါ် သတင်းပို့ခြင်း"""
    if not Config.TELEGRAM_TOKEN or not Config.ALLOWED_USER_ID:
        return
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": Config.ALLOWED_USER_ID, "text": message}
    try:
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")

def check_jarvis_health():
    """Port 8000 တွင် Jarvis အသက်ရှင်ခြင်း ရှိ/မရှိ စစ်ဆေးခြင်း"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex(('127.0.0.1', Config.PORT))
    sock.close()
    return result == 0 

def recover_jarvis():
    """၂ ဆင့်ပါသော အသက်ပြန်သွင်းသည့် စနစ်"""
    logger.error("Jarvis is DOWN! Initiating recovery...")

    # ==========================================
    # အဆင့် (၁): ရိုးရိုး Restart အရင်လုပ်ကြည့်မည် (Soft Recovery) - ဤအဆင့်ကို အမြဲအရင်လုပ်မည်
    # ==========================================
    logger.info("Attempting Soft Restart...")
    subprocess.run(["pkill", "-f", "python3 main.py"], stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    subprocess.Popen("nohup venv/bin/python main.py >> jarvis.log 2>&1 &", shell=True)
    time.sleep(10) # Jarvis အပြည့်အဝ နိုးလာရန် ၁၀ စက္ကန့်ခန့် အချိန်ပေးမည်

    if check_jarvis_health():
        send_alert("**[SOFT RECOVERY SUCCESSFUL]**\nSystem Restored! All Systems are Fully Operational, Sir!")
        logger.info("Soft Recovery Successful.")
        return

    # ==========================================
    # အဆင့် (၂): Soft Restart လုံးဝ မရတော့မှသာ GitHub မှ ဆွဲချမည် (Hard Recovery)
    # ==========================================
    send_alert("🚨 **[HARD RECOVERY INITIATED]**\nSystem Restored! All Systems are Fully Operational, Sir!")
    logger.warning("Soft restart failed. Executing Git Hard Reset...")

    try:
        subprocess.run(["git", "fetch", "origin", "main"], check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
        subprocess.run(["git", "clean", "-fd"], check=True)

        logger.info("Restarting Jarvis after Hard Reset...")
        subprocess.Popen("nohup venv/bin/python main.py >> jarvis.log 2>&1 &", shell=True)
        time.sleep(10)

        if check_jarvis_health():
            send_alert("✅ **[HARD RECOVERY SUCCESSFUL]**\nGitHub မှ Stable Code ဖြင့် Jarvis ကို အောင်မြင်စွာ အသက်ပြန်သွင်းလိုက်ပါပြီ။")
            logger.info("Hard Recovery Successful.")
        else:
            send_alert("❌ **[FATAL ERROR]**\nGitHub မှ Code ဖြင့်လည်း အသက်ပြန်သွင်း၍ မရပါ။ ကျေးဇူးပြု၍ Server သို့ ဝင်ရောက် စစ်ဆေးပေးပါ ဆရာ။")
            logger.critical("Failed to restart Jarvis even after Hard Reset!")
    except Exception as e:
        logger.error(f"Error during hard recovery: {e}")
        send_alert(f"⚠️ **[RECOVERY FAILED]**\nError: {e}")

def cleanup_logs():
    """ညသန်းခေါင်ယံ Log ရှင်းလင်းရေး (နောက်ဆုံး လိုင်း ၁၀၀၀ သာ ချန်မည်)"""
    # ဆရာတောင်းဆိုထားသော Log ၃ ခုလုံး ပါဝင်သည်
    logs_to_clean = ["jarvis.log", "server.log", "watchdog.log", "messenger_automation.log"]
    for log_file in logs_to_clean:
        if os.path.exists(log_file):
            os.system(f"tail -n 800 {log_file} > {log_file}.tmp && mv {log_file}.tmp {log_file}")
    logger.info("Log cleanup completed for jarvis.log, server.log, and watchdog.log.")

# ================= MAIN LOOP =================
logger.info("🛡️ Supervisor Watchdog Started. Guarding Jarvis 24/7...")
last_cleanup_date = None

while True:
    # 1. Health Monitoring (စက္ကန့် ၃၀ လျှင် တစ်ခါ စစ်ဆေးမည်)
    if not check_jarvis_health():
        recover_jarvis()

    # 2. Daily Log Cleanup (config.py ထဲမှ Timezone အတိုင်း စစ်ဆေးမည်)
    current_time = datetime.now(Config.TIMEZONE)
    current_date = current_time.date()

    if current_time.hour == 0 and last_cleanup_date != current_date:
        cleanup_logs()
        send_alert("🧹 **[SYSTEM MAINTENANCE]**\nညသန်းခေါင်ယံ Log Cleanup အောင်မြင်စွာ ပြီးစီးပါပြီ။ jarvis.log, server.log နှင့် watchdog.log တို့ကို ရှင်းလင်းပေးလိုက်ပါပြီ ဆရာ။")
        last_cleanup_date = current_date

    time.sleep(30)