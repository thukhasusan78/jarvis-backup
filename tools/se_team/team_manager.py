import logging
import os
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool

logger = logging.getLogger("SE_TEAM_MANAGER")

class SETeamManagerTool(BaseTool):
    """
    SE Team ကြီးတစ်ခုလုံးကို ကြီးကြပ်မယ့် Project Manager Tool ပါ။
    CEO က Project အကြီးတွေ (ဥပမာ- App ရေးတာ၊ Website ရေးတာ) ဆိုရင် ဒီ Tool ကို လှမ်းသုံးပါမယ်။
    """
    name = "manage_se_team"
    description = "Delegate a full software engineering project to the SE Team. Use this when the user asks to build an app, website, or complex software project."
    owner_role = "ceo" # CEO သာလျှင် ဒီ Tool ကို သုံးခွင့်ရှိသည်

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "project_name": types.Schema(
                type=types.Type.STRING, 
                description="A short, no-spaces name for the project folder (e.g., 'hotel_app', 'bitcoin_tracker')."
            ),
            "project_description": types.Schema(
                type=types.Type.STRING, 
                description="Full detailed description of what needs to be built."
            )
        }

    def get_required(self) -> List[str]:
        return ["project_name", "project_description"]

    async def execute(self, **kwargs) -> str:
        from core.agent import JarvisAgent
        project_name = kwargs.get("project_name")
        project_desc = kwargs.get("project_description")

        logger.info(f"🚀 SE Team Manager received new project: {project_name}")

        # ၁။ Project အတွက် သီးသန့် အလုပ်ရုံ (Folder) တည်ဆောက်ခြင်း
        project_dir = os.path.join("workspace", "projects", project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        plan_file_path = os.path.join(project_dir, "plan.md").replace("\\", "/")

        # ၂။ Planner Agent ဆီသို့ အလုပ်စတင် လွှဲပြောင်းပေးခြင်း
        logger.info("🧠 Step 1: Calling Planner Agent...")
        
        # Planner အတွက် သီးသန့် Agent တစ်ကောင် မွေးဖွားမယ်
        planner_agent = JarvisAgent(role="planner")

        # 🧠 FIX: Planner ရဲ့ ဦးနှောက် (planner.md) ကို ဖတ်ပြီး အတင်းထည့်သွင်းပေးခြင်း
        prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'planner.md')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                planner_agent.brain.system_instruction = f.read()

        # Planner ကို အမိန့်ပေးမယ်
        prompt = f"""
        PROJECT NAME: {project_name}
        DESCRIPTION: {project_desc}
        
        MISSION:
        You are the Chief Software Architect. Do NOT write functional code yet.
        1. Design the architecture and folder structure for this project.
        2. Create a step-by-step execution plan (Phase 1, Phase 2, etc.).
        3. Save this detailed plan into a file named exactly '{plan_file_path}' using your 'manage_file' tool.
        """        
        
        # 🚀 AUTO-PIPELINE (Planner -> Researcher -> Coder)
        try:
            # --- [STAGE 1: PLANNER] ---
            logger.info("🧠 STAGE 1: Architecting Plan...")
            await planner_agent.chat(prompt, user_id=999999)
            
            # --- [STAGE 2: RESEARCHER] ---
            logger.info("🕵️ STAGE 2: Researching Tech Stack...")
            researcher_agent = JarvisAgent(role="researcher")
            r_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'researcher.md')
            if os.path.exists(r_prompt_path):
                with open(r_prompt_path, 'r', encoding='utf-8') as f:
                    researcher_agent.brain.system_instruction = f.read()
                    
            r_msg = f"PROJECT: {project_name}\nRead the plan.md, research the best practices, and output 'final_blueprint.md'."
            await researcher_agent.chat(r_msg, user_id=999999)
            
            # --- [STAGE 3: CODER] ---
            logger.info("👨‍💻 STAGE 3: Writing Code...")
            coder_agent = JarvisAgent(role="coder")
            c_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'coder.md')
            if os.path.exists(c_prompt_path):
                with open(c_prompt_path, 'r', encoding='utf-8') as f:
                    coder_agent.brain.system_instruction = f.read()
                    
            c_msg = f"PROJECT: {project_name}\nRead 'final_blueprint.md', strictly build the exact folder structure, and write the complete code for ALL Phases outlined in the blueprint. Do not stop until the entire functional project is built."
            coder_result = await coder_agent.chat(c_msg, user_id=999999)
            
            # --- [STAGE 4: HUMAN-IN-THE-LOOP (CREDENTIAL HANDSHAKE)] ---
            logger.info("🔐 STAGE 4: Checking .env for missing credentials...")
            env_path = os.path.join(os.getcwd(), 'workspace', 'projects', project_name, '.env')
            missing_keys = []
            
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        if "=" in line:
                            key, val = line.strip().split("=", 1)
                            # Key နေရာမှာ အလွတ်ဖြစ်နေတာ၊ သို့မဟုတ် Placeholder (ဥပမာ- your_api_key_here) ဖြစ်နေတာတွေကို ရှာဖွေမည်
                            if not val or "your_" in val.lower() or "here" in val.lower() or val == '""' or val == "''":
                                missing_keys.append(key)
            
            if missing_keys:
                hitl_msg = f"✅ SE Team Pipeline (Coding Phase) Completed!\n\n[LEAD DEVELOPER REPORT]:\n{coder_result}\n\n"
                hitl_msg += f"🛑 HUMAN-IN-THE-LOOP REQUIRED: The project needs the following API Keys in the `.env` file: **{', '.join(missing_keys)}**.\n\n"
                hitl_msg += f"👉 INSTRUCTION FOR YOU (JARVIS): Tell the Sir that the code is ready, but you need the API keys. Ask him to provide the keys directly in this chat. Inform him that once he provides the keys, YOU will automatically use 'manage_file' to update the .env file and then you will start the QA Testing."
                return hitl_msg
            else:
                return f"✅ SE Team Pipeline Completed!\n\n[LEAD DEVELOPER REPORT]:\n{coder_result}\n\n(Note: No missing API keys detected. Project is ready. You can now automatically proceed to use 'manage_qa_testing' to test the code.)"

        except Exception as e:
            logger.error(f"Manager Pipeline Error: {e}")
            return f"❌ SE Team Pipeline encountered an error: {str(e)}"