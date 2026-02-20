import os
import logging
from pathlib import Path
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("JARVIS_FILE_MANAGER")

class FileManagerTool(BaseTool):
    """
    Secure File System Manager (Sandbox Mode).
    Allows Jarvis to read any project file, but strictly limits writing to specific folders.
    """
    name = "manage_file"
    description = "Read, write, or list files. STRICT SANDBOX RULES: You can read any file in the project. But you can ONLY write files to 'custom_skills', 'workspace', or 'memory' directories."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING, 
                enum=["read", "write", "list"], 
                description="Action to perform: 'read' (read file), 'write' (create/modify file), 'list' (list directory contents)."
            ),
            "path": types.Schema(
                type=types.Type.STRING, 
                description="Relative path to the file or directory (e.g., 'core/agent.py' or 'custom_skills/my_tool.py')."
            ),
            "content": types.Schema(
                type=types.Type.STRING, 
                description="The text content to write into the file (Required ONLY for 'write' action)."
            )
        }

    def get_required(self) -> List[str]:
        return ["action", "path"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        file_path_str = kwargs.get("path")
        content = kwargs.get("content", "")

        try:
            # လုံခြုံရေး - လက်ရှိ Project Folder လမ်းကြောင်းကို ယူမည်
            base_dir = Path.cwd().resolve()
            target_path = (base_dir / file_path_str).resolve()

            # 🛑 လုံခြုံရေး အဆင့် ၁: Project Folder အပြင်ဘက်ကို ထွက်ခွင့်မပြုပါ
            if not str(target_path).startswith(str(base_dir)):
                return "🛑 Security Alert: Access denied. You are restricted to the project directory only."

            # 🛑 လုံခြုံရေး အဆင့် ၂: Write Access ကို Sandbox Folder များတွင်သာ ခွင့်ပြုမည်
            if action == "write":
                allowed_dirs = ["custom_skills", "workspace", "memory"]
                is_allowed = any(str(target_path).startswith(str((base_dir / d).resolve())) for d in allowed_dirs)
                
                if not is_allowed:
                    return f"🛑 Security Alert: Write access denied for '{file_path_str}'. To prevent system corruption, you are only allowed to write in: {', '.join(allowed_dirs)}."

            # --- လုပ်ဆောင်ချက်များ (Actions) ---
            if action == "read":
                if not target_path.exists() or not target_path.is_file():
                    return f"Error: File '{file_path_str}' does not exist."
                with open(target_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                return f"📄 Contents of {file_path_str}:\n\n{file_content}"

            elif action == "write":
                # Folder မရှိသေးပါက အလိုအလျောက် တည်ဆောက်ပေးမည်
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"✅ Successfully wrote data to '{file_path_str}'."

            elif action == "list":
                if not target_path.exists() or not target_path.is_dir():
                    return f"Error: Directory '{file_path_str}' does not exist."
                items = os.listdir(target_path)
                return f"📂 Directory listing for {file_path_str}:\n" + "\n".join(items)

            else:
                return f"Error: Unknown action '{action}'."

        except Exception as e:
            logger.error(f"FileManager Error: {e}")
            return f"File operation failed: {str(e)}"