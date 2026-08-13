import os
import paramiko
import logging
from pathlib import Path
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool
from core.security import is_secret_path

logger = logging.getLogger("JARVIS_MIGRATION")

KNOWN_HOSTS = os.path.expanduser("~/.ssh/known_hosts")


class MigrationTool(BaseTool):
    """
    Zips non-secret project data and transfers via SFTP with host-key verification.
    """
    name = "manage_migration"
    description = (
        "Zip memory/prompts/skills (NEVER .env or sessions) and transfer via SFTP. "
        "Requires known_hosts entry for the remote host."
    )
    owner_role = "sysadmin"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["zip_memory", "sftp_upload"],
                description="'zip_memory' compresses safe folders. 'sftp_upload' transfers a file."
            ),
            "local_file": types.Schema(
                type=types.Type.STRING,
                description="Path to local file (e.g., 'workspace/jarvis_migration_data.zip')."
            ),
            "remote_path": types.Schema(
                type=types.Type.STRING,
                description="Destination path on remote server."
            ),
            "host": types.Schema(type=types.Type.STRING, description="Remote Server IP"),
            "username": types.Schema(type=types.Type.STRING, description="SSH Username"),
            "password": types.Schema(type=types.Type.STRING, description="SSH Password"),
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")

        if action == "zip_memory":
            try:
                logger.info("📦 Zipping Important Files for Migration...")
                import zipfile

                os.makedirs("workspace", exist_ok=True)
                zip_path = "workspace/jarvis_migration_data.zip"
                targets = ["memory", "custom_skills", "core/prompts"]
                base = Path.cwd().resolve()

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for target in targets:
                        if os.path.isdir(target):
                            for root, _, files in os.walk(target):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    if is_secret_path(file_path, base):
                                        logger.info(f"Skipping secret from zip: {file_path}")
                                        continue
                                    zipf.write(file_path, arcname=file_path)
                        elif os.path.isfile(target) and not is_secret_path(target, base):
                            zipf.write(target, arcname=target)

                return (
                    f"✅ Success: Memory, prompts, and skills zipped to '{zip_path}'. "
                    "Secrets (.env/sessions/keys) were excluded."
                )
            except Exception as e:
                return f"❌ Failed to zip files: {str(e)}"

        if action == "sftp_upload":
            host = kwargs.get("host")
            user = kwargs.get("username")
            pwd = kwargs.get("password")
            local_f = kwargs.get("local_file")
            remote_p = kwargs.get("remote_path")

            if not all([host, user, pwd, local_f, remote_p]):
                return "Error: host, username, password, local_file, and remote_path are all required for sftp_upload."

            if not os.path.exists(local_f):
                return f"Error: Local file '{local_f}' does not exist. Did you zip it first?"

            if is_secret_path(local_f):
                return "🛑 Security Alert: Refusing to upload secret/credential files."

            try:
                logger.info(f"📤 Uploading {local_f} to {host}:{remote_p} via SFTP...")
                client = paramiko.SSHClient()
                if os.path.exists(KNOWN_HOSTS):
                    client.load_host_keys(KNOWN_HOSTS)
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
                client.connect(
                    hostname=host,
                    username=user,
                    password=pwd,
                    timeout=15,
                    look_for_keys=False,
                    allow_agent=False,
                )
                sftp = client.open_sftp()
                sftp.put(local_f, remote_p)
                sftp.close()
                client.close()
                return f"✅ Success: File '{local_f}' successfully uploaded to '{host}:{remote_p}'."
            except Exception as e:
                msg = str(e).replace(pwd or "", "***")
                logger.error(f"SFTP Upload Failed: {msg}")
                return (
                    f"❌ SFTP Upload Failed: {msg}. "
                    "Ensure the host key exists in ~/.ssh/known_hosts (RejectPolicy is enforced)."
                )

        return f"Error: Unknown action '{action}'."
