import os
import logging
from pathlib import Path
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from core.security import is_secret_path

logger = logging.getLogger("JARVIS_FILE_MANAGER")


class FileManagerTool(BaseTool):
    """
    Secure File System Manager (Sandbox Mode).
    Read is allowed inside the project except secrets; write is limited to sandbox dirs.
    """
    name = "manage_file"
    description = (
        "Read, write, or list files. STRICT SANDBOX: cannot read .env/session/key files. "
        "Write only to 'custom_skills', 'workspace', or 'memory'."
    )

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["read", "write", "list"],
                description="Action to perform: 'read', 'write', or 'list'."
            ),
            "path": types.Schema(
                type=types.Type.STRING,
                description="Relative path to the file or directory."
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="Text content for 'write' action."
            )
        }

    def get_required(self) -> List[str]:
        return ["action", "path"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        file_path_str = kwargs.get("path")
        content = kwargs.get("content", "")

        if not file_path_str:
            return "❌ Error: 'path' parameter is required but was not provided."

        try:
            base_dir = Path.cwd().resolve()
            target_path = (base_dir / file_path_str).resolve()

            if not str(target_path).startswith(str(base_dir)):
                return "🛑 Security Alert: Access denied. You are restricted to the project directory only."

            if is_secret_path(target_path, base_dir):
                return "🛑 Security Alert: Access denied. Secret/credential files cannot be read, written, or listed."

            if action == "write":
                allowed_dirs = ["custom_skills", "workspace", "memory"]
                is_allowed = any(
                    str(target_path).startswith(str((base_dir / d).resolve()))
                    for d in allowed_dirs
                )
                if not is_allowed:
                    return (
                        f"🛑 Security Alert: Write access denied for '{file_path_str}'. "
                        f"Allowed write dirs: {', '.join(allowed_dirs)}."
                    )
                # Also block writing secrets into allowed dirs
                if is_secret_path(target_path.name) or target_path.name.startswith(".env"):
                    return "🛑 Security Alert: Cannot write secret/credential filenames."

            if action == "read":
                if not target_path.exists() or not target_path.is_file():
                    return f"Error: File '{file_path_str}' does not exist."
                with open(target_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                return f"📄 Contents of {file_path_str}:\n\n{file_content}"

            if action == "write":
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return (
                    f"✅ SUCCESS: File '{file_path_str}' has been written. "
                    "CRITICAL INSTRUCTION: You MUST NOT edit this file again. "
                    "STOP using tools immediately and send your final text report to the user."
                )

            if action == "list":
                if not target_path.exists() or not target_path.is_dir():
                    return f"Error: Directory '{file_path_str}' does not exist."
                items = []
                for name in os.listdir(target_path):
                    if is_secret_path(target_path / name, base_dir):
                        continue
                    items.append(name)
                return f"📂 Directory listing for {file_path_str}:\n" + "\n".join(items)

            return f"Error: Unknown action '{action}'."

        except Exception as e:
            logger.error(f"FileManager Error: {e}")
            return f"File operation failed: {str(e)}"
