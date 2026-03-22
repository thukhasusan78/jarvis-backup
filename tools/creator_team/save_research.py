import os
import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_CREATOR_TEAM")

class SaveResearchTool(BaseTool):
    """
    Saves the final synthesized Deep Research Brief into a markdown file.
    """
    name = "save_research_brief"
    description = "Save the final synthesized research brief into a markdown file so the Writer Agent can use it later."
    owner_role = "deep_researcher"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "topic": types.Schema(
                type=types.Type.STRING,
                description="The main topic of the research (e.g., 'DeepSeek_AI')."
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="The full synthesized markdown content of the research brief."
            )
        }

    def get_required(self) -> List[str]:
        return ["topic", "content"]

    async def execute(self, **kwargs) -> str:
        topic = kwargs.get("topic")
        content = kwargs.get("content")
        
        save_dir = os.path.abspath("workspace/research_briefs")
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"{topic}_brief.md")
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"✅ Research Brief saved at: {file_path}")
            return f"✅ SUCCESS: Research Brief saved successfully at '{file_path}'."
        except Exception as e:
            return f"Error saving file: {str(e)}"