import psutil
import logging
import datetime
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_RESOURCE")

class ResourceTool(BaseTool):
    """
    Server တစ်ခုလုံးရဲ့ အသေးစိတ် ကျန်းမာရေးကို စစ်ဆေးခြင်း
    (OpenInterpreter လိုမျိုး Process အလိုက် မြင်ရမည်)
    """
    name = "check_resource"
    description = "Check current RAM, CPU usage and Disk space."

    def get_parameters(self) -> Dict[str, types.Schema]:
        # ဒီ Tool က Parameter ဘာမှ မလိုပါဘူး။
        return {}

    def get_required(self) -> List[str]:
        return []

    async def execute(self, **kwargs) -> str:
        try:
            # 1. အခြေခံ အချက်အလက်များ
            cpu_usage = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

            # 2. RAM အများဆုံးစားနေသော Process ၅ ခု (The Real Culprits)
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    p_info = proc.info
                    processes.append(p_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # RAM အလိုက် စီမယ်
            top_ram = sorted(processes, key=lambda p: p['memory_percent'], reverse=True)[:5]
            
            # 3. Report ထုတ်မယ်
            report = f"""
**SERVER DEEP SCAN REPORT**
--------------------------------
**Uptime:** Since {boot_time}
**CPU Usage:** {cpu_usage}%
**RAM Usage:** {ram.percent}% ({ram.used // (1024*1024)}MB / {ram.total // (1024*1024)}MB)
**Disk Usage:** {disk.percent}% (Free: {disk.free // (1024*1024*1024)}GB)

**TOP 5 RAM CONSUMERS:**\n"""
            for p in top_ram:
                report += f"- **{p['name']}** (PID: {p['pid']}): {p['memory_percent']:.2f}% RAM\n"

            return report

        except Exception as e:
            return f"Error checking resources: {str(e)}"