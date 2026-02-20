from typing import Dict, Any, List
from google.genai import types

class BaseTool:
    """
    Tool အားလုံးရဲ့ ဖခင် (Base Template).
    Tool အသစ်ရေးတိုင်း ဒီ Class ကို Inherit လုပ်ရပါမယ်။
    """
    name: str = "base_tool"
    description: str = "Base description"
    owner_role: str = "all"  # 'ceo', 'web_surfer', 'sysadmin', 'researcher', သို့မဟုတ် 'all'
    
    def get_parameters(self) -> Dict[str, types.Schema]:
        """
        Tool အတွက် လိုအပ်တဲ့ parameters များကို ကြေညာရန် (Gemini Schema Format)
        """
        return {}

    def get_required(self) -> List[str]:
        """
        မဖြစ်မနေ လိုအပ်တဲ့ parameters စာရင်း
        """
        return []

    def get_declaration(self) -> types.FunctionDeclaration:
        """
        Brain (Gemini) က နားလည်မယ့် Function Schema ကို အလိုအလျောက် ထုတ်ပေးပါတယ်။
        ဒီ Function လေးရှိသွားတဲ့အတွက် core/brain.py ထဲမှာ ရှည်လျားတဲ့ Schema တွေ
        သွားရေးစရာ မလိုတော့ပါဘူး။
        """
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties=self.get_parameters(),
                required=self.get_required()
            )
        )

    async def execute(self, **kwargs) -> str:
        """
        Tool အလုပ်လုပ်မယ့် Main Logic ကို ဒီမှာရေးရပါမယ်။
        (Subclass တွေက ဒါကို အစားထိုးရေးရပါမယ်)
        """
        raise NotImplementedError(f"Tool '{self.name}' must implement the 'execute' method.")