import os
import time
import subprocess
import socket
import logging
from datetime import datetime
import psutil
import requests
from config import Config 
import re
import subprocess

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
    # အဆင့် (၁): Soft Recovery
    # ==========================================
    logger.info("Attempting Soft Restart...")
    
    # 🔥 FIX: main.py ရော၊ Port 8000 ကိုင်ထားတဲ့ကောင်တွေကိုပါ အမြစ်ပြတ် ရှင်းလင်းမည်
    subprocess.run(["pkill", "-f", "main.py"], stderr=subprocess.DEVNULL)
    subprocess.run(["fuser", "-k", f"{Config.PORT}/tcp"], stderr=subprocess.DEVNULL) 
    time.sleep(3) # သေချာ ပိတ်သွားအောင် ၃ စက္ကန့် စောင့်မည်
    
    # venv ထဲက python ကို တိုက်ရိုက်ခေါ်သုံးထားလို့ venv အလိုလို ဝင်ပြီးသား ဖြစ်ပါသည်
    subprocess.Popen("nohup venv/bin/python main.py >> jarvis.log 2>&1 &", shell=True)
    time.sleep(10)

    if check_jarvis_health():
        send_alert("**[SOFT RECOVERY SUCCESSFUL]**\nSystem Restored! All Systems are Fully Operational, Sir!")
        logger.info("Soft Recovery Successful.")
        return

    # ==========================================
    # 🛑 HARD RECOVERY (Git Reset) ကို အပြီးတပိုင် ပိတ်ထားသည် (2026-08-13)
    # အကြောင်းရင်း - git reset --hard / git clean -fd က Local WIP Code များကို
    # အကြိမ်ပေါင်းများစွာ ဖျက်ပစ်ခဲ့ဖူးသည်။ ဤနေရာတွင် Git Working Tree ကို
    # ဘယ်အချိန်မှ အလိုအလျောက် မထိတော့ပါ။ Soft Restart မရလျှင် ဆရာ့ကိုသာ အကြောင်းကြားမည်။
    # ==========================================
    send_alert(
        "**[FATAL ERROR]**\n"
        "Soft Restart ဖြင့် Jarvis ကို အသက်ပြန်သွင်း၍ မရပါ။\n"
        "Local Code များ ဆုံးရှုံးမှုမရှိစေရန် Git Hard Recovery ကို ပိတ်ထားပါပြီ။\n"
        "ကျေးဇူးပြု၍ Server သို့ ဝင်ရောက် စစ်ဆေးပေးပါ ဆရာ။"
    )
    logger.critical("Soft restart failed. Hard recovery is DISABLED to protect local work. Manual intervention required.")

def cleanup_logs():
    """ညသန်းခေါင်ယံ Log ရှင်းလင်းရေး (နောက်ဆုံး လိုင်း ၁၀၀၀ သာ ချန်မည်)"""
    # ဆရာတောင်းဆိုထားသော Log ၃ ခုလုံး ပါဝင်သည်
    logs_to_clean = ["jarvis.log", "server.log", "watchdog.log"]
    for log_file in logs_to_clean:
        if os.path.exists(log_file):
            os.system(f"tail -n 800 {log_file} > {log_file}.tmp && mv {log_file}.tmp {log_file}")
    logger.info("Log cleanup completed for jarvis.log, server.log, and watchdog.log.")

# --- 🛡️ THE WATCHTOWER: INTRUSION DETECTION SYSTEM ---
alerted_ips = set() # သတိပေးပြီးသား IP တွေကို မှတ်ထားရန်

def check_intrusions():
    """SSH မှတစ်ဆင့် Password အကြိမ်ကြိမ်မှားပြီး ဝင်ရောက်ရန် ကြိုးစားနေသူများကို စစ်ဆေးခြင်း"""
    global alerted_ips
    try:
        # Ubuntu/Debian တွင် SSH log များသည် auth.log တွင် ရှိသည်
        log_file = "/var/log/auth.log"
        if not os.path.exists(log_file):
            return
        
        # နောက်ဆုံး လိုင်း ၁၀၀ ကို ဖတ်မည်
        result = subprocess.run(['tail', '-n', '100', log_file], capture_output=True, text=True)
        logs = result.stdout
        
        # 'Failed password' စာသားပါသော လိုင်းများမှ IP များကို ဆွဲထုတ်မည်
        failed_ips = re.findall(r"Failed password for .* from ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", logs)
        
        # IP တစ်ခုချင်းစီ ဘယ်နှစ်ခါ မှားလဲ ရေတွက်မည်
        ip_counts = {}
        for ip in failed_ips:
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
            
        # ၅ ခါထက် ပိုမှားနေသော IP များကို Report တင်မည်
        for ip, count in ip_counts.items():
            if count >= 5 and ip not in alerted_ips:
                alert_msg = f"🚨 **[SECURITY ALERT: BRUTE-FORCE DETECTED]**\n"
                alert_msg += f"ဆရာ၊ တစ်စုံတစ်ယောက်က Server ကို SSH မှတစ်ဆင့် ဖောက်ဝင်ရန် ကြိုးစားနေပါသည်။\n\n"
                alert_msg += f"Hacker IP: `{ip}`\n"
                alert_msg += f"Failed Attempts: {count} times (in recent logs)\n\n"
                alert_msg += f"`shell_exec` ကိုသုံး၍ `ufw deny from {ip}` ဟုရိုက်ကာ ချက်ချင်း Block လိုက်ပါ။"
                
                send_alert(alert_msg)
                logger.warning(f"Intrusion Alert Sent for IP: {ip}")
                
                # ထပ်ခါထပ်ခါ စာမပို့အောင် မှတ်ထားမည်
                alerted_ips.add(ip)
                
    except Exception as e:
        logger.error(f"Intrusion Detection Error: {e}")
# ----------------------------------------------------    

# ================= MAIN LOOP =================
logger.info("Supervisor Watchdog Started. Guarding Jarvis 24/7...")
last_cleanup_date = None
high_load_counter = 0  # CPU/RAM တက်နေတဲ့ အကြိမ်ရေကို မှတ်ရန်

while True:
    # 1. Health Monitoring (Jarvis သေသွားရင် ပြန်နှိုးမည်)
    if not check_jarvis_health():
        recover_jarvis()

    # 2. Proactive Environmental Awareness (Background Monitoring)
    try:
        # ၁ စက္ကန့်စာ CPU ကို ဖတ်မည်
        current_cpu = psutil.cpu_percent(interval=1)
        current_ram = psutil.virtual_memory().percent
        
        # CPU 85% သို့မဟုတ် RAM 90% ကျော်နေပါက
        if current_cpu > 85 or current_ram > 90:
            high_load_counter += 1
            # ၆ ကြိမ် (၆ * ၃၀ စက္ကန့် = ၃ မိနစ်) ဆက်တိုက် ဖြစ်နေမှ Alert ပို့မည် (ခဏလေး တက်တာကို မပို့အောင်)
            if high_load_counter >= 6:
                alert_msg = f"**[SYSTEM ALERT: HIGH RESOURCE USAGE]**\n"
                alert_msg += f"Sir, Server တွင် ဝန်ပိနေပုံရပါသည်။\n"
                alert_msg += f"CPU Usage: {current_cpu}%\n"
                alert_msg += f"RAM Usage: {current_ram}%\n\n"
                alert_msg += f"`check_resource` tool ကိုသုံးပြီး စစ်ဆေးခိုင်းနိုင်ပါသည်။ သို့မဟုတ် ပြဿနာရှာရန် ကျွန်တော့်ကို အမိန့်ပေးပါ။"
                
                send_alert(alert_msg)
                logger.warning(f"High Load Detected! CPU: {current_cpu}%, RAM: {current_ram}%")
                
                # Alert ပို့ပြီးပါက နောက်ထပ် ၁၅ မိနစ် (အကြိမ် ၃၀) နေမှ ထပ်စစ်ရန် Reset ချမည် (Alert တွေ ဆက်တိုက်မဝင်အောင်)
                high_load_counter = -30 
        else:
            # ပုံမှန် ပြန်ဖြစ်သွားရင် Counter ပြန်စမည်
            if high_load_counter > 0:
                high_load_counter = 0
                
    except Exception as e:
        logger.error(f"Resource Monitoring Error: {e}")

    # 3. Security Monitoring (Hacker များ ဝင်ရန်ကြိုးစားမှု ရှိမရှိ စစ်ဆေးမည်)
    check_intrusions()    

    # 4. Daily Log Cleanup
    current_time = datetime.now(Config.TIMEZONE)
    current_date = current_time.date()

    if current_time.hour == 0 and last_cleanup_date != current_date:
        cleanup_logs()
        send_alert("**[SYSTEM MAINTENANCE]**\nညသန်းခေါင်ယံ Log Cleanup အောင်မြင်စွာ ပြီးစီးပါပြီ။")
        last_cleanup_date = current_date

    time.sleep(30)