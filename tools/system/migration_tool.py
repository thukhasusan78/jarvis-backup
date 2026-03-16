import os
import shutil
import paramiko
import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_MIGRATION")

class MigrationTool(BaseTool):
    """
    Handles the heavy lifting of Server Migration: Zipping Memory and SFTP File Transfer.
    """
    name = "manage_migration"
    description = "Zip the entire 'memory' folder (brain/databases) and securely transfer it to a remote server via SFTP."
    owner_role = "sysadmin"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["zip_memory", "sftp_upload"],
                description="'zip_memory' compresses the memory folder. 'sftp_upload' transfers a file to the remote server."
            ),
            "local_file": types.Schema(
                type=types.Type.STRING, 
                description="Path to local file (e.g., 'workspace/memory_backup.zip'). Required for upload."
            ),
            "remote_path": types.Schema(
                type=types.Type.STRING, 
                description="Destination path on remote server (e.g., '/root/memory_backup.zip'). Required for upload."
            ),
            "host": types.Schema(type=types.Type.STRING, description="Remote Server IP"),
            "username": types.Schema(type=types.Type.STRING, description="SSH Username"),
            "password": types.Schema(type=types.Type.STRING, description="SSH Password")
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")

        if action == "zip_memory":
            try:
                logger.info("📦 Zipping Memory (Databases)...")
                # memory/ folder တစ်ခုလုံးကို zip ချုံ့ပြီး workspace/ ထဲ သိမ်းမည်
                os.makedirs("workspace", exist_ok=True)
                shutil.make_archive("workspace/memory_backup", 'zip', "memory")
                return "✅ Success: Memory folder zipped successfully to 'workspace/memory_backup.zip'."
            except Exception as e:
                return f"❌ Failed to zip memory: {str(e)}"

        elif action == "sftp_upload":
            host = kwargs.get("host")
            user = kwargs.get("username")
            pwd = kwargs.get("password")
            local_f = kwargs.get("local_file")
            remote_p = kwargs.get("remote_path")

            if not all([host, user, pwd, local_f, remote_p]):
                return "Error: host, username, password, local_file, and remote_path are all required for sftp_upload."

            if not os.path.exists(local_f):
                return f"Error: Local file '{local_f}' does not exist. Did you zip it first?"

            try:
                logger.info(f"📤 Uploading {local_f} to {host}:{remote_p} via SFTP...")
                
                # SFTP ဖြင့် လုံခြုံစွာ ဖိုင်ပို့ခြင်း
                transport = paramiko.Transport((host, 22))
                transport.connect(username=user, password=pwd)
                sftp = paramiko.SFTPClient.from_transport(transport)

                sftp.put(local_f, remote_p)

                sftp.close()
                transport.close()
                return f"✅ Success: File '{local_f}' successfully uploaded to '{host}:{remote_p}'."
            except Exception as e:
                return f"❌ SFTP Upload Failed: {str(e)}"