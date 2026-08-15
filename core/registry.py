import os
import importlib
import inspect
import logging
from typing import Dict, List, Optional
from google.genai import types

from tools.base import BaseTool
from core.security import role_allowed

logger = logging.getLogger("TOOL_REGISTRY")


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._discover_and_load_tools("tools")
        self.reload_custom_tools()

    def reload_custom_tools(self):
        """Reload tools from custom_skills/ after Agent writes new ones."""
        if os.path.exists("custom_skills"):
            self._discover_and_load_tools("custom_skills")

    def _discover_and_load_tools(self, package_name: str = "tools"):
        package_dir = os.path.join(os.getcwd(), package_name)

        for root, dirs, files in os.walk(package_dir):
            if "__pycache__" in root:
                continue

            for file in files:
                if file.endswith(".py") and file != "__init__.py" and file != "base.py":
                    module_rel_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                    module_name = module_rel_path.replace(os.path.sep, ".")[:-3]

                    try:
                        module = importlib.import_module(module_name)

                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, BaseTool) and obj is not BaseTool:
                                tool_instance = obj()
                                self._tools[tool_instance.name] = tool_instance
                                logger.info(f"🔌 Tool တွဲချိတ်ပြီးပါပြီ: {tool_instance.name} (from {module_name})")
                    except Exception as e:
                        logger.error(f"❌ '{module_name}' ကို ခေါ်ယူရာတွင် အမှားဖြစ်နေသည်: {e}")

    def get_tool(self, tool_name: str) -> BaseTool:
        return self._tools.get(tool_name)

    def resolve_owner_role(self, tool: BaseTool):
        """Apply folder heuristics when a tool leaves owner_role as 'all'."""
        assigned_role = getattr(tool, "owner_role", "all")

        if assigned_role == "all":
            module = tool.__module__

            if tool.name == "publish_event":
                assigned_role = "all"
            elif "tools.system.business_tools" in module:
                assigned_role = ["business_manager", "secretary"]
            elif "tools.system" in module:
                if tool.name in ["delegate_task", "manage_schedule", "report_to_sir", "manual_movie_trigger"]:
                    assigned_role = "ceo"
                else:
                    assigned_role = "sysadmin"
            elif "tools.web" in module:
                assigned_role = "researcher"
            elif "tools.memory" in module:
                assigned_role = "ceo"
            elif "custom_skills" in module:
                # Custom skills stay restricted to ceo unless they set owner_role explicitly
                assigned_role = "ceo"

        return assigned_role

    def get_declarations_for_role(self, role: str) -> List[types.FunctionDeclaration]:
        declarations = []
        for tool in self._tools.values():
            assigned_role = self.resolve_owner_role(tool)
            # web tools: deep_researcher and ceo (voice HUD answers directly) may also see researcher tools
            if assigned_role == "researcher" and role in ("deep_researcher", "ceo"):
                assigned_role = role
            if role_allowed(role, assigned_role):
                declarations.append(tool.get_declaration())
        return declarations

    def is_tool_allowed_for_role(self, tool_name: str, role: Optional[str]) -> bool:
        if tool_name not in self._tools:
            return False
        if role is None:
            return False
        tool = self._tools[tool_name]
        assigned_role = self.resolve_owner_role(tool)
        if assigned_role == "researcher" and role in ("deep_researcher", "ceo"):
            assigned_role = role
        return role_allowed(role, assigned_role)

    async def execute_tool(self, tool_name: str, caller_role: Optional[str] = None, **kwargs) -> str:
        """
        Execute a registered tool. Role is enforced at runtime (not only at declaration).
        """
        if tool_name not in self._tools:
            return f"Error: Tool '{tool_name}' ကို Registry တွင် ရှာမတွေ့ပါ။"

        if caller_role is not None and not self.is_tool_allowed_for_role(tool_name, caller_role):
            logger.warning(f"⛔ Role '{caller_role}' blocked from tool '{tool_name}'")
            return f"⛔ Access Denied: role '{caller_role}' is not allowed to execute '{tool_name}'."

        try:
            tool = self._tools[tool_name]
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' အလုပ်လုပ်ရာတွင် Error တက်သွားသည်: {e}")
            return f"Tool Execution Error ({tool_name}): {str(e)}"


tool_registry = ToolRegistry()
