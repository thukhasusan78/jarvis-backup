import os
os.environ["OMP_NUM_THREADS"] = "1"           # 🔥 CPU ကို တစ်ခုတည်းပဲ သုံးခိုင်းမယ်
os.environ["TOKENIZERS_PARALLELISM"] = "false" # 🔥 Thread တွေ အများကြီးပွားတာကို ပိတ်မယ်
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from memory.vector_storage import vector_storage
from config import Config

logger = logging.getLogger("JARVIS_ANALYZER")

class CodebaseAnalyzerTool(BaseTool):
    name = "analyze_codebase"
    description = "Scan a project directory, summarize the files, and save the architecture map into the Vector Database."
    owner_role = "sysadmin"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "target_path": types.Schema(type=types.Type.STRING, description="The root directory to analyze"),
            "project_name": types.Schema(type=types.Type.STRING, description="A name or label for this project")
        }

    def get_required(self) -> List[str]:
        return ["target_path", "project_name"]

    async def execute(self, **kwargs) -> str:
        target_path = kwargs.get("target_path")
        project_name = kwargs.get("project_name")
        
        if not os.path.exists(target_path): return f"❌ Error: The directory '{target_path}' does not exist."

        ignored_folders = [".git", "__pycache__", "venv", "env", "memory", "workspace", "custom_skills", "node_modules"] 
        batch_data = [] 

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignored_folders]
            for file in files:
                if file.endswith(('.py', '.html', '.md', '.txt', '.json', '.js', '.css')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read(1000) # Token ပိုသက်သာအောင် 1000 ပဲထားလိုက်မယ်
                            summary = f"File Content Prefix:\n```\n{content}\n...\n```"
                    except Exception:
                        summary = "Cannot read file content."

                    batch_data.append({
                        "id": uuid.uuid4().hex,
                        "category": "Directory_Map",
                        "search_text": f"Problem: {file_path}\nSolution: {project_name}\nCode: {summary}",
                        "task_or_query": file_path,
                        "solution": project_name,
                        "code_snippet": summary,
                        "timestamp": datetime.now(Config.TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                    })

        if batch_data:
            try:
                if vector_storage.table is None: vector_storage._init_db()
                if vector_storage.table:
                    try:
                        vector_storage.table.delete(f"solution = '{project_name}'")
                    except Exception:
                        pass
                    chunk_size = 5 
                    for i in range(0, len(batch_data), chunk_size):
                        chunk = batch_data[i:i + chunk_size]
                        await asyncio.to_thread(vector_storage.table.add, chunk)
                        await asyncio.sleep(1) 
                        
                    return f"✅ အောင်မြင်စွာ Analyze လုပ်ပြီးပါပြီ။ Project '{project_name}' ကို Update လုပ်လိုက်ပါပြီ။"
            except Exception as e:
                return f"❌ Error: {str(e)}"
        return f"⚠️ မှတ်သားစရာ ဖိုင်မတွေ့ပါ။"