import subprocess
import logging
import datetime
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_GIT")

class GitBackupTool(BaseTool):
    """
    Auto-pushes all code changes to GitHub.
    """
    name = "backup_code"
    description = "Backup current project code to GitHub repository."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "message": types.Schema(
                type=types.Type.STRING, 
                description="Commit message (optional)"
            )
        }

    def get_required(self) -> List[str]:
        return [] # Message က မထည့်လည်းရလို့ အလွတ်ထားထားတယ်

    async def execute(self, **kwargs) -> str:
        commit_message = kwargs.get("message")
        try:
            # 1. Check Status (ပြောင်းလဲမှု ရှိမရှိ စစ်မယ်)
            status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
            
            if not status.stdout.strip():
                return "No changes detected. Everything is already up-to-date."

            # 2. Git Add (ဖိုင်အကုန်လုံးကို ထည့်မယ်)
            subprocess.run("git add .", shell=True, check=True)

            # 3. Git Commit (မှတ်တမ်းတင်မယ်)
            if not commit_message:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_message = f"Auto-backup by JARVIS: {timestamp}"
            
            subprocess.run(f'git commit -m "{commit_message}"', shell=True, check=True)

            # 4. Git Push (GitHub ပေါ်တင်မယ်)
            result = subprocess.run("git push -u origin main", shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                return f"Successfully pushed code to GitHub!\nCommit: '{commit_message}'"
            else:
                return f"Push Failed:\n{result.stderr}"

        except Exception as e:
            return f"Git Error: {str(e)}"