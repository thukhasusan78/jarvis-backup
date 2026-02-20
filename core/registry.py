import os
import importlib
import inspect
import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("TOOL_REGISTRY")

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._discover_and_load_tools("tools")
        self.reload_custom_tools() # Tool အသစ်တွေကိုပါ ဆွဲသွင်းမယ်

    def reload_custom_tools(self):
        """Agent က Tool အသစ်ရေးပြီးတိုင်း Auto Update လုပ်ပေးမည့်စနစ်"""
        if os.path.exists("custom_skills"):
            self._discover_and_load_tools("custom_skills")

    def _discover_and_load_tools(self, package_name: str = "tools"):
        """
        tools/ folder အောက်က .py ဖိုင်မှန်သမျှကို အလိုအလျောက် လိုက်ရှာပြီး 
        BaseTool subclass တွေကို Register လုပ်ပေးမယ့် စနစ်။
        """
        package_dir = os.path.join(os.getcwd(), package_name)
        
        # 1. tools/ အောက်က folder တွေ၊ ဖိုင်တွေကို လိုက်မွှေမယ်
        for root, dirs, files in os.walk(package_dir):
            if "__pycache__" in root:
                continue
                
            for file in files:
                if file.endswith(".py") and file != "__init__.py" and file != "base.py":
                    # ဖိုင်လမ်းကြောင်းကို Python Module နာမည်ပြောင်းမယ် (ဥပမာ: tools.system.shell)
                    module_rel_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                    module_name = module_rel_path.replace(os.path.sep, ".")[:-3]
                    
                    try:
                        # Module ကို Dynamic လှမ်းခေါ်မယ်
                        module = importlib.import_module(module_name)
                        
                        # ထို Module ထဲမှာ BaseTool ကို inherit လုပ်ထားတဲ့ Class တွေကို ရှာမယ်
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, BaseTool) and obj is not BaseTool:
                                tool_instance = obj() # Class ကို အသက်သွင်းမယ်
                                self._tools[tool_instance.name] = tool_instance
                                logger.info(f"🔌 Tool တွဲချိတ်ပြီးပါပြီ: {tool_instance.name} (from {module_name})")
                    except Exception as e:
                        logger.error(f"❌ '{module_name}' ကို ခေါ်ယူရာတွင် အမှားဖြစ်နေသည်: {e}")

    def get_declarations_for_role(self, role: str) -> List[types.FunctionDeclaration]:
        """Role အလိုက် သင့်တော်တဲ့ Tool များကိုသာ ရွေးထုတ်ပေးမည့် Auto-Router"""
        declarations = []
        for tool in self._tools.values():
            assigned_role = getattr(tool, "owner_role", "all")
            
            # Built-in Tool များအတွက် Folder ပေါ်မူတည်ပြီး Auto-Assign လုပ်ခြင်း
            if assigned_role == "all":
                module = tool.__module__
                if "tools.browser" in module:
                    assigned_role = "web_surfer"
                elif "tools.system" in module:
                    if tool.name in ["delegate_task", "manage_schedule"]:
                        assigned_role = "ceo"
                    else:
                        assigned_role = "sysadmin"
                elif "tools.web" in module:
                    assigned_role = "researcher"
                elif "tools.memory" in module:
                    assigned_role = "ceo"
                elif "custom_skills" in module:
                    assigned_role = "all" # အသစ်ရေးတဲ့ Tool တွေကို အကုန်သုံးခွင့်ပေးမယ်

            # ကိုယ့် Role နဲ့ ကိုက်ညီရင် (သို့) အကုန်သုံးလို့ရတဲ့ Tool ဆိုရင် ခေါင်းထဲထည့်ပေးမယ်
            if assigned_role == "all" or assigned_role == role:
                declarations.append(tool.get_declaration())
                
        return declarations

    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """
        Agent က Tool နာမည်ပေးလိုက်ရင် သက်ဆိုင်ရာ execute function ကို ပြေးခေါ်ပေးမယ်။
        (agent.py မှာ if/else တွေ လုံးဝ မလိုတော့ဘူး)
        """
        if tool_name not in self._tools:
            return f"Error: Tool '{tool_name}' ကို Registry တွင် ရှာမတွေ့ပါ။"
        
        try:
            tool = self._tools[tool_name]
            # Tool ရဲ့ execute function ကို kwargs တွေ ထည့်ပြီး run မယ်
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' အလုပ်လုပ်ရာတွင် Error တက်သွားသည်: {e}")
            return f"Tool Execution Error ({tool_name}): {str(e)}"

# Singleton Instance ထုတ်ထားမယ် (တစ်နေရာက ခေါ်လည်း ဒီကောင်ပဲ အလုပ်လုပ်မယ်)
tool_registry = ToolRegistry()