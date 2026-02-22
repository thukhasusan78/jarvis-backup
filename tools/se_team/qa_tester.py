import logging
import os
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("SE_QA_TESTER")

class QATesterTool(BaseTool):
    """
    QA Tester Tool for SE Team. 
    Project ပြီးသွားရင် Run ကြည့်မယ်၊ Error တက်ရင် Coder ဆီ အလိုလို ပြန်ပို့ပြီး ပြင်ခိုင်းမယ့် စနစ်။
    """
    name = "manage_qa_testing"
    description = "Run Quality Assurance (QA), Security checks, and Execution tests on a completed project. It automatically loops back to the developer if bugs are found."
    owner_role = "ceo"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "project_name": types.Schema(
                type=types.Type.STRING, 
                description="The name of the project folder to test (e.g., 'Password_Generator')."
            )
        }

    def get_required(self) -> List[str]:
        return ["project_name"]

    async def execute(self, **kwargs) -> str:
        # Circular Import မဖြစ်အောင် Function အထဲရောက်မှ Agent ကို ခေါ်မယ်
        from core.agent import JarvisAgent 
        
        project_name = kwargs.get("project_name")
        logger.info(f"🔎 Initiating QA Testing for Project: {project_name}")
        # --- 🛑 PRE-FLIGHT CHECK: HUMAN-IN-THE-LOOP (API KEYS) ---
        env_path = os.path.join(os.getcwd(), 'workspace', 'projects', project_name, '.env')
        missing_keys = []
        
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        if not val or "your_" in val.lower() or "here" in val.lower() or val == '""' or val == "''":
                            missing_keys.append(key)
        
        if missing_keys:
            logger.warning(f"QA Halted: Missing keys detected -> {missing_keys}")
            hitl_msg = f"🛑 QA PRE-FLIGHT HALTED: Missing API Keys in `.env`.\n"
            hitl_msg += f"Missing Keys: **{', '.join(missing_keys)}**\n\n"
            hitl_msg += f"👉 INSTRUCTION FOR JARVIS (CRITICAL): \n"
            hitl_msg += f"1. Tell the Sir that QA testing cannot proceed because the above API keys are missing.\n"
            hitl_msg += f"2. Provide the EXACT OFFICIAL URL/LINK where the Sir can generate or find the keys for {', '.join(missing_keys)} (e.g., if it's COINGECKO_API_KEY, give the CoinGecko developer dashboard link).\n"
            hitl_msg += f"3. Ask the Sir to paste the key directly here. Inform him that once he provides it, YOU will automatically use 'manage_file' to update the .env file and then you will re-run the QA Tester."
            return hitl_msg

        max_loops = 3  # Error တက်တိုင်း အဆုံးမရှိ ပတ်မနေအောင် (၃) ကြိမ်ပဲ အများဆုံး ပြင်ခိုင်းမယ်
        current_loop = 1

        while current_loop <= max_loops:
            logger.info(f"🔄 QA Loop {current_loop}/{max_loops}...")

            # --- 1. QA Agent ကို အလုပ်ခိုင်းခြင်း ---
            qa_agent = JarvisAgent(role="qa_tester")
            qa_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'qa_tester.md')
            if os.path.exists(qa_prompt_path):
                with open(qa_prompt_path, 'r', encoding='utf-8') as f:
                    qa_agent.brain.system_instruction = f.read()

            qa_msg = f"PROJECT: {project_name}\nRead the 'final_blueprint.md' and the written code. Run the code using your 'shell_exec' tool. Output [STATUS: PASSED] or [STATUS: FAILED] with a detailed bug report."
            
            qa_result = await qa_agent.chat(qa_msg, user_id=999999)

            # --- 2. ရလဒ်ကို စစ်ဆေးခြင်း ---
            if "[STATUS: PASSED]" in qa_result:
                return f"✅ QA Testing Passed for '{project_name}'!\n\n[QA REPORT]:\n{qa_result}\n\n🚀 System is now ready for Deployment!"
            
            elif "[STATUS: FAILED]" in qa_result:
                logger.warning(f"⚠️ QA Failed. Sending back to Coder...")
                
                # --- 3. Error တက်ရင် Coder ဆီ အလိုလို ပြန်ပို့ခြင်း ---
                coder_agent = JarvisAgent(role="coder")
                c_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'coder.md')
                if os.path.exists(c_prompt_path):
                    with open(c_prompt_path, 'r', encoding='utf-8') as f:
                        coder_agent.brain.system_instruction = f.read()
                
                fix_msg = f"PROJECT: {project_name}\nCRITICAL: QA testing FAILED with the following report:\n\n{qa_result}\n\nPlease read the affected files, FIX the code, and save the changes using 'manage_file'."
                
                logger.info("👨‍💻 Coder is fixing the bugs...")
                await coder_agent.chat(fix_msg, user_id=999999)
                
                current_loop += 1
            else:
                # မျက်စိလည်ပြီး Status မထည့်ပေးလိုက်ရင် လုံခြုံရေးအရ Failed လို့ပဲ သတ်မှတ်မယ်
                logger.warning("QA Agent did not provide a STATUS tag. Retrying...")
                current_loop += 1

        return f"❌ QA Loop exhausted. The project '{project_name}' still has errors after {max_loops} fixing attempts. Manual intervention required."