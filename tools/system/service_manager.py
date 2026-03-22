import subprocess
import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_SERVICE_MANAGER")

class ServiceManagerTool(BaseTool):
    """
    Manage Linux Services (systemd).
    Allows Jarvis to start, stop, restart, or check the status of services like Nginx, PostgreSQL, etc.
    """
    name = "manage_service"
    description = "Manage systemd services on the VPS. Use this to start, stop, restart, or check the status of services (e.g., nginx, postgresql, docker)."
    owner_role = "sysadmin"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["start", "stop", "restart", "status"],
                description="What to do with the service."
            ),
            "service_name": types.Schema(
                type=types.Type.STRING,
                description="The exact name of the service (e.g., 'nginx', 'postgresql')."
            )
        }

    def get_required(self) -> List[str]:
        return ["action", "service_name"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        service_name = kwargs.get("service_name")
        
        logger.info(f"⚙️ Managing Service: {action} -> {service_name}")
        
        try:
            # လုံခြုံရေးအရ အန္တရာယ်ရှိသော သင်္ကေတများကို ပိတ်ပင်မည်
            if ";" in service_name or "&" in service_name or "|" in service_name:
                return "🛑 Security Alert: Invalid characters in service name."

            command = f"sudo systemctl {action} {service_name}"
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                if action == "status":
                    return f"✅ Status of '{service_name}':\n{result.stdout.strip()}"
                return f"✅ Successfully executed '{action}' on service '{service_name}'."
            else:
                return f"❌ Failed to {action} '{service_name}'.\nError Logs:\n{result.stderr.strip()}"
                
        except Exception as e:
            logger.error(f"Service Manager Error: {e}")
            return f"Service Execution Error: {str(e)}"