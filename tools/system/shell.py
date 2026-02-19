import subprocess
import logging
import signal
import os
from typing import Dict, List
from google.genai import types

# ဖခင် Class ကို လှမ်းခေါ်မယ်
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_SHELL")

# ⛔ မူရင်း Safety List (လုံးဝ မလျှော့ဘူး)
PROTECTED_ITEMS = [
    "core", "tools", "memory", "interfaces", "main.py", "config.py", 
    "tasks", "venv", ".env", ".git", "/etc", "/boot", "/bin"
]

class ShellTool(BaseTool):
    """
    Executes Linux shell commands on the VPS. 
    ENHANCED: Captures Timeouts & Partial Logs for Self-Correction.
    """
    name = "shell_exec"
    description = "Execute Linux terminal commands on the VPS. USE WITH CAUTION."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "command": types.Schema(
                type=types.Type.STRING, 
                description="The Linux command to execute."
            )
        }

    def get_required(self) -> List[str]:
        return ["command"]

    async def execute(self, **kwargs) -> str:
        command = kwargs.get("command")
        if not command:
            return "Error: No command provided."

        # --- 🛡️ SMART SAFETY CHECK (မူရင်း Logic) ---
        dangerous_keywords = ["rm ", "mv ", ">", "truncate", "dd "]
        is_destructive = any(keyword in command for keyword in dangerous_keywords)
        
        if is_destructive:
            for protected in PROTECTED_ITEMS:
                if protected in command:
                    logger.warning(f"⛔ Blocked dangerous command: {command}")
                    return f"⛔ SAFETY ALERT: Access Denied! Target '{protected}' is a CORE file."
        # ------------------------------------

        logger.info(f"💻 Executing: {command}")
        
        try:
            # Timeout ကို ၆၀ စက္ကန့်ထားမယ် (User Interaction လိုရင် မြန်မြန်သိအောင်)
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=60 
            )
            
            output = f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"\nSTDERR (Error Logs):\n{result.stderr}"
                
            return output.strip() or "Command executed successfully (No output)."

        except subprocess.TimeoutExpired as e:
            # 🔥 THE UPGRADE: Timeout ဖြစ်ရင် ရသလောက် Log ကို ပြန်ပို့မယ်
            partial_output = ""
            if e.stdout: partial_output += f"STDOUT:\n{e.stdout.decode('utf-8', errors='ignore')}\n"
            if e.stderr: partial_output += f"STDERR:\n{e.stderr.decode('utf-8', errors='ignore')}\n"
            
            return f"⚠️ TIMEOUT ALERT: The command stopped because it took too long.\nLOGS CAPTURED:\n{partial_output}\n(Hint: Is it waiting for 'yes/no' input?)"

        except Exception as e:
            return f"System Execution Error: {str(e)}"