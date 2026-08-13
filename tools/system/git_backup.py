import subprocess
import logging
import datetime
from typing import Dict, List
from google.genai import types
from config import Config

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_GIT")


class GitBackupTool(BaseTool):
    """
    Auto-pushes project code to GitHub using argv-based git commands (no shell interpolation).
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
        return []

    def _run(self, argv: List[str], check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(argv, shell=False, capture_output=True, text=True, check=check)

    async def execute(self, **kwargs) -> str:
        commit_message = kwargs.get("message")
        try:
            status = self._run(["git", "status", "--porcelain"])
            if not status.stdout.strip():
                return "No changes detected. Everything is already up-to-date."

            # Stage tracked + untracked project files, but never force-add secrets via shell
            self._run(["git", "add", "-A"], check=True)

            # Unstage secrets if gitignore failed somehow
            for secret in [".env", "*.session", "*.pem", "*.key"]:
                self._run(["git", "reset", "HEAD", "--", secret])

            if not commit_message:
                timestamp = datetime.datetime.now(Config.TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                commit_message = f"Auto-backup by JARVIS: {timestamp}"

            # Never interpolate message into a shell string — pass as argv
            commit = self._run(["git", "commit", "-m", commit_message])
            if commit.returncode != 0 and "nothing to commit" in (commit.stdout + commit.stderr).lower():
                return "No changes detected after excluding secrets."
            if commit.returncode != 0:
                return f"Commit Failed:\n{commit.stderr or commit.stdout}"

            result = self._run(["git", "push", "-u", "origin", "HEAD"])
            if result.returncode == 0:
                return f"Successfully pushed code to GitHub!\nCommit: '{commit_message}'"
            return f"Push Failed:\n{result.stderr}"

        except Exception as e:
            return f"Git Error: {str(e)}"
