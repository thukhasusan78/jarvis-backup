import subprocess
import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_FIREWALL")

class FirewallManagerTool(BaseTool):
    """
    Manage the UFW Firewall.
    Allows Jarvis to block malicious IPs or open/close specific ports.
    """
    name = "manage_firewall"
    description = "Manage the UFW (Uncomplicated Firewall). Use this to DENY malicious IPs, or ALLOW specific ports for new deployments."
    owner_role = "sysadmin"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["allow", "deny", "status", "delete"],
                description="Action to perform. 'allow' to open port, 'deny' to block IP/Port, 'status' to check rules, 'delete' to remove a rule."
            ),
            "target": types.Schema(
                type=types.Type.STRING,
                description="The IP address (e.g., '192.168.1.5') or Port number (e.g., '80/tcp', '8080') to target. Leave empty for 'status'."
            )
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        target = kwargs.get("target", "")

        logger.info(f"🧱 Firewall Action: {action} -> {target}")

        try:
            if action == "status":
                result = subprocess.run("sudo ufw status numbered", shell=True, capture_output=True, text=True)
                return f"🛡️ Firewall Status:\n{result.stdout.strip()}"

            if not target:
                return f"Error: 'target' (IP or Port) is required for '{action}' action."

            # 🛑 SAFETY LOCKS (မိမိကိုယ်ကို ပြန်မပိတ်မိစေရန်)
            if action == "deny" and target in ["22", "22/tcp"]:
                return "🛑 CRITICAL ERROR: You cannot block Port 22 (SSH). Sir will be locked out of the server!"
            if action == "deny" and target in ["8000", "8000/tcp"]:
                return "🛑 CRITICAL ERROR: You cannot block Port 8000. It is your own API Port!"

            # Command တည်ဆောက်ခြင်း
            if action == "delete":
                command = f"sudo ufw --force delete {target}" # target က rule number ဖြစ်ရမည်
            else:
                command = f"sudo ufw {action} {target}"

            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                # Firewall Update လုပ်ပြီးတိုင်း အသက်ဝင်အောင် Reload လုပ်မည်
                subprocess.run("sudo ufw reload", shell=True, capture_output=True)
                return f"✅ Firewall rule applied successfully: '{action}' -> '{target}'."
            else:
                return f"❌ Firewall command failed.\nError:\n{result.stderr.strip()}"

        except Exception as e:
            logger.error(f"Firewall Manager Error: {e}")
            return f"Firewall Execution Error: {str(e)}"