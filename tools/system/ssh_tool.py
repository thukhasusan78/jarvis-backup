import os
import paramiko
import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_SSH_TOOL")

KNOWN_HOSTS = os.path.expanduser("~/.ssh/known_hosts")


class SSHRemoteTool(BaseTool):
    """
    Execute shell commands on a REMOTE server via SSH with host-key verification.
    Passwords are never logged.
    """
    name = "ssh_remote_exec"
    description = (
        "Execute Linux commands on a REMOTE server via SSH. "
        "Host must already exist in ~/.ssh/known_hosts (RejectPolicy)."
    )
    owner_role = "sysadmin"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "host": types.Schema(
                type=types.Type.STRING,
                description="Remote server IP address."
            ),
            "username": types.Schema(
                type=types.Type.STRING,
                description="SSH username (usually 'root')."
            ),
            "password": types.Schema(
                type=types.Type.STRING,
                description="SSH password for the remote server (never logged)."
            ),
            "command": types.Schema(
                type=types.Type.STRING,
                description="The Linux command to execute on the remote server."
            )
        }

    def get_required(self) -> List[str]:
        return ["host", "username", "password", "command"]

    async def execute(self, **kwargs) -> str:
        host = kwargs.get("host")
        username = kwargs.get("username")
        password = kwargs.get("password")
        command = kwargs.get("command")

        # Never log password
        logger.info(f"🌐 Connecting to Remote Server: {username}@{host}")

        client = paramiko.SSHClient()
        if os.path.exists(KNOWN_HOSTS):
            client.load_host_keys(KNOWN_HOSTS)
        # Reject unknown hosts — do NOT AutoAdd (MITM risk)
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

        try:
            client.connect(
                hostname=host,
                username=username,
                password=password,
                timeout=15,
                look_for_keys=False,
                allow_agent=False,
            )

            logger.info(f"💻 Executing remote command on {host}")
            stdin, stdout, stderr = client.exec_command(command)

            out = stdout.read().decode("utf-8", errors="ignore").strip()
            err = stderr.read().decode("utf-8", errors="ignore").strip()

            result = ""
            if out:
                result += f"STDOUT:\n{out}\n"
            if err:
                result += f"STDERR:\n{err}\n"

            if not result:
                return f"✅ [Success] Command executed silently on remote server {host}."
            return f"📡 Remote Execution Result from {host}:\n{result}"

        except Exception as e:
            # Avoid echoing password if present in exception strings
            msg = str(e).replace(password or "", "***")
            logger.error(f"SSH Error on {host}: {msg}")
            return (
                f"❌ SSH Connection/Execution Error: {msg}. "
                "Ensure the host key is in ~/.ssh/known_hosts."
            )
        finally:
            client.close()
