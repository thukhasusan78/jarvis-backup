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
        # Tool တွေကို သိမ်းထားမယ့် Dictionary (ဥပမာ - {"search_web": SearchToolInstance})
        self._tools: Dict[str, BaseTool] = {}
        self._discover_and_load_tools()

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

    def get_all_declarations(self) -> List[types.FunctionDeclaration]:
        """
        Brain (Gemini) ဆီ ပို့ပေးဖို့ Tool အားလုံးရဲ့ Schema တွေကို စုထုတ်ပေးမယ်။
        (Brain.py မှာ ဒါလေး တစ်ကြောင်းခေါ်လိုက်ရုံနဲ့ Tool အကုန်ရပြီ)
        """
        return [tool.get_declaration() for tool in self._tools.values()]

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