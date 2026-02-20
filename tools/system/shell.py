import subprocess
import logging
import signal
import os
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_SHELL")

PROTECTED_ITEMS = [
    "core", "tools", "memory", "interfaces", "main.py", "config.py", 
    "tasks", "venv", ".env", ".git", "/etc", "/boot", "/bin"
]

class ShellTool(BaseTool):
    """
    Executes Linux shell commands on the VPS. 
    ENHANCED: Properly handles silent success without confusing the AI.
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

        # --- 🛡️ SMART SAFETY CHECK ---
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
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=60 
            )
            
            # 🔥 FIX: STDOUT အလွတ်ကြီး ထွက်မလာအောင် သေချာစစ်ထုတ်မယ်
            output = ""
            if result.stdout and result.stdout.strip():
                output += f"STDOUT:\n{result.stdout.strip()}\n"
            if result.stderr and result.stderr.strip():
                output += f"STDERR (Error Logs):\n{result.stderr.strip()}"
                
            final_output = output.strip()
            
            # Output လုံးဝမရှိရင် AI နားလည်အောင် Success လို့ တိတိကျကျ ပြောပြမယ်
            if not final_output:
                return "[Success] Command executed silently with no errors. Task completed."
                
            return final_output

        except subprocess.TimeoutExpired as e:
            partial_output = ""
            if e.stdout: partial_output += f"STDOUT:\n{e.stdout.decode('utf-8', errors='ignore')}\n"
            if e.stderr: partial_output += f"STDERR:\n{e.stderr.decode('utf-8', errors='ignore')}\n"
            
            return f"⚠️ TIMEOUT ALERT: The command stopped because it took too long.\nLOGS CAPTURED:\n{partial_output}\n(Hint: Is it waiting for 'yes/no' input?)"

        except Exception as e:
            return f"System Execution Error: {str(e)}"