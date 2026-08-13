import shlex
import subprocess
import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from core.security import path_contains_any

logger = logging.getLogger("JARVIS_SHELL")

PROTECTED_ITEMS = [
    "core", "tools", "memory", "interfaces", "main.py", "config.py",
    "tasks", "venv", ".env", ".git", "/etc", "/boot", "/bin", "/usr/bin",
    "supervisor.py", "watchdog.py",
]

# Shell metacharacters that imply interactive shell features — blocked under argv mode
SHELL_META = set("|&;<>`$(){}[]!*?\n\r")


class ShellTool(BaseTool):
    """
    Executes Linux commands on the VPS using argv lists (no shell interpolation).
    """
    name = "shell_exec"
    description = (
        "Execute a single Linux command on the VPS as an argv list (no shell pipes/redirection). "
        "Example: 'ls -la workspace'. USE WITH CAUTION."
    )

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "command": types.Schema(
                type=types.Type.STRING,
                description="Single command with args, e.g. 'df -h'. No pipes, redirects, or shell metacharacters."
            )
        }

    def get_required(self) -> List[str]:
        return ["command"]

    async def execute(self, **kwargs) -> str:
        command = kwargs.get("command")
        if not command:
            return "Error: No command provided."

        command = command.strip()
        if any(ch in command for ch in SHELL_META):
            return (
                "⛔ SAFETY ALERT: Shell metacharacters (pipes, redirects, substitutions) are not allowed. "
                "Pass a single command with plain arguments."
            )

        if path_contains_any(command, PROTECTED_ITEMS):
            # Allow read-only inspection of project dirs via ls/cat/head/tail/stat
            argv_probe = shlex.split(command)
            read_only = {"ls", "cat", "head", "tail", "stat", "du", "wc", "file", "pwd", "whoami", "df", "free", "ps", "top", "uptime"}
            if not argv_probe or argv_probe[0] not in read_only:
                logger.warning(f"⛔ Blocked protected-path command: {command}")
                return "⛔ SAFETY ALERT: Access Denied! That command targets a protected core path."

        try:
            argv = shlex.split(command)
        except ValueError as e:
            return f"Error: Could not parse command: {e}"

        if not argv:
            return "Error: Empty command."

        # Block clearly destructive binaries regardless of args
        blocked_bins = {"rm", "mkfs", "dd", "shutdown", "reboot", "poweroff", "halt", "userdel", "passwd"}
        if argv[0] in blocked_bins:
            return f"⛔ SAFETY ALERT: Binary '{argv[0]}' is blocked."

        logger.info(f"💻 Executing argv: {argv}")

        try:
            result = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = ""
            if result.stdout and result.stdout.strip():
                output += f"STDOUT:\n{result.stdout.strip()}\n"
            if result.stderr and result.stderr.strip():
                output += f"STDERR (Error Logs):\n{result.stderr.strip()}"

            final_output = output.strip()
            if not final_output:
                if result.returncode != 0:
                    return f"[Failed] Command exited with code {result.returncode} and no output."
                return "[Success] Command executed silently with no errors. Task completed."
            if result.returncode != 0:
                return f"[Exit {result.returncode}]\n{final_output}"
            return final_output

        except subprocess.TimeoutExpired as e:
            partial_output = ""
            if e.stdout:
                partial_output += f"STDOUT:\n{e.stdout if isinstance(e.stdout, str) else e.stdout.decode('utf-8', errors='ignore')}\n"
            if e.stderr:
                partial_output += f"STDERR:\n{e.stderr if isinstance(e.stderr, str) else e.stderr.decode('utf-8', errors='ignore')}\n"
            return f"⚠️ TIMEOUT ALERT: The command stopped because it took too long.\nLOGS CAPTURED:\n{partial_output}"

        except Exception as e:
            return f"System Execution Error: {str(e)}"
