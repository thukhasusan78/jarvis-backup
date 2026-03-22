import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from memory.memory_controller import memory_controller

logger = logging.getLogger("JARVIS_KNOWLEDGE_TOOL")

class KnowledgeTool(BaseTool):
    """
    Save or search advanced knowledge, problem-solving skills, and past mistakes in the Vector Database.
    """
    name = "manage_knowledge"
    description = "Save or search advanced knowledge, problem-solving skills, and past mistakes in the Vector Database. Use this to remember how you solved an error, or to search for past solutions."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["save", "search", "delete"],
                description="Whether to 'save', 'search', or 'delete' past experiences."
            ),
            "category": types.Schema(
                type=types.Type.STRING,
                enum=["Skill", "Mistake", "Fact"],
                description="Category of the knowledge (required for 'save'). 'Skill' for solutions, 'Mistake' for errors to avoid."
            ),
            "task_or_query": types.Schema(
                type=types.Type.STRING,
                description="The problem faced, or the topic to remember (required for 'save')."
            ),
            "solution": types.Schema(
                type=types.Type.STRING,
                description="How it was solved, or the detailed fact (required for 'save')."
            ),
            "code_snippet": types.Schema(
                type=types.Type.STRING,
                description="Any related code snippet (optional for 'save')."
            ),
            "search_query": types.Schema(
                type=types.Type.STRING,
                description="What to search for in the memory (required for 'search')."
            )
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        
        try:
            if action == "save":
                cat = kwargs.get("category")
                task = kwargs.get("task_or_query")
                sol = kwargs.get("solution")
                code = kwargs.get("code_snippet", "")
                
                if not cat or not task or not sol:
                    return "Error: 'category', 'task_or_query', and 'solution' are required to save knowledge."
                    
                success = memory_controller.save_knowledge(cat, task, sol, code)
                if success:
                    return f"✅ Experience saved successfully to Deep Memory as [{cat}]."
                return "❌ Failed to save knowledge to Vector DB."
                
            elif action == "search":
                query = kwargs.get("search_query")
                if not query:
                    return "Error: 'search_query' is required to search."
                    
                results = memory_controller.search_knowledge(query)
                if results:
                    return results
                return "No relevant past knowledge found in Deep Memory."

            elif action == "delete":
                query = kwargs.get("search_query")
                if not query:
                    return "Error: 'search_query' is required to delete."
                    
                if memory_controller.delete_knowledge(query):
                    return f"✅ Knowledge related to '{query}' has been permanently deleted from Deep Memory."
                return "❌ Failed to find or delete the specified knowledge. It might not exist."    
                
            else:
                return f"Error: Unknown action '{action}'."
                
        except Exception as e:
            logger.error(f"Knowledge Tool Error: {e}")
            return f"Knowledge Tool Error: {str(e)}"