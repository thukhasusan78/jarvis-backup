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
            ),
            "command": types.Schema(
                type=types.Type.STRING,
                description="Pipeline command: 'start_new' (Plan+UI), 'revise_frontend' (Fix UI), or 'build_backend' (Run backend after UI is locked)."
            ),
            "feedback": types.Schema(
                type=types.Type.STRING,
                description="User's feedback for frontend revision."
            )
        }

    def get_required(self) -> List[str]:
        # မူရင်း project_description ကို ပြန်ထည့်ထားပါသည်
        return ["project_name", "project_description"]

    async def execute(self, **kwargs) -> str:
        from core.agent import JarvisAgent
        project_name = kwargs.get("project_name")
        project_desc = kwargs.get("project_description")
        command = kwargs.get("command", "start_new")
        feedback = kwargs.get("feedback", "")

        logger.info(f"🚀 SE Team Manager received command '{command}' for project: {project_name}")

        # ၁။ Project အတွက် သီးသန့် အလုပ်ရုံ (Folder) တည်ဆောက်ခြင်း
        project_dir = os.path.join("workspace", "projects", project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        plan_file_path = os.path.join(project_dir, "plan.md").replace("\\", "/")

        try:
            # ==========================================
            # လမ်းကြောင်း (၁): ပရောဂျက်အသစ်စတင်ခြင်း (UI အရင်ထုတ်မည်)
            # ==========================================
            if command == "start_new":
                logger.info("🧠 STAGE 1: Architecting Plan...")
                planner_agent = JarvisAgent(role="planner")
                prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'planner.md')
                if os.path.exists(prompt_path):
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        planner_agent.brain.system_instruction = f.read()

                prompt = f"""
                PROJECT NAME: {project_name}
                DESCRIPTION: {project_desc}
                
                MISSION:
                You are the Chief Software Architect. Do NOT write functional code yet.
                1. Design the architecture and folder structure for this project.
                2. Create a step-by-step execution plan (Phase 1, Phase 2, etc.).
                3. Save this detailed plan into a file named exactly '{plan_file_path}' using your 'manage_file' tool.
                """        
                await planner_agent.chat(prompt, user_id=999999)

                logger.info("🕵️ STAGE 2: Researching Tech Stack...")
                researcher_agent = JarvisAgent(role="researcher")
                r_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'researcher.md')
                if os.path.exists(r_prompt_path):
                    with open(r_prompt_path, 'r', encoding='utf-8') as f:
                        researcher_agent.brain.system_instruction = f.read()
                        
                r_msg = f"PROJECT: {project_name}\nRead the plan.md, research the best practices, and output 'final_blueprint.md'."
                await researcher_agent.chat(r_msg, user_id=999999)

                logger.info("🎨 STAGE 3: Building UI Prototype...")
                frontend_agent = JarvisAgent(role="frontend_coder")
                f_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'frontend_coder.md')
                if os.path.exists(f_prompt_path):
                    with open(f_prompt_path, 'r', encoding='utf-8') as f:
                        frontend_agent.brain.system_instruction = f.read()
                        
                f_msg = f"PROJECT: {project_name}\nRead 'final_blueprint.md'. Build the UI using mock data. Save it in a 'frontend' or 'public' folder. Stop when done."
                f_result = await frontend_agent.chat(f_msg, user_id=999999)
                
                hitl_msg = f"🎨 **UI PROTOTYPE READY!**\n\n[FRONTEND REPORT]:\n{f_result}\n\n"
                hitl_msg += f"👉 **INSTRUCTION FOR JARVIS:** Tell the Sir to open the HTML files in `workspace/projects/{project_name}/` and review the UI visually.\n"
                hitl_msg += f"Tell him: 'Sir, please review the UI. If you want to change colors, layout, or components, just tell me. If you love it, reply with **LOCK UI** so I can start building the Backend.'"
                return hitl_msg

            # ==========================================
            # လမ်းကြောင်း (၂): UI ကို စိတ်ကြိုက် ပြင်ဆင်ခြင်း
            # ==========================================
            elif command == "revise_frontend":
                logger.info("🎨 REVISING UI...")
                frontend_agent = JarvisAgent(role="frontend_coder")
                f_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'frontend_coder.md')
                if os.path.exists(f_prompt_path):
                    with open(f_prompt_path, 'r', encoding='utf-8') as f:
                        frontend_agent.brain.system_instruction = f.read()
                
                f_msg = f"PROJECT: {project_name}\nThe user wants to change the UI. FEEDBACK: {feedback}\nPlease read the existing UI files, apply these exact changes, and save them."
                f_result = await frontend_agent.chat(f_msg, user_id=999999)
                return f"🎨 **UI UPDATED!**\n\n{f_result}\n\n👉 Ask the Sir to review again. Reply 'LOCK UI' if satisfied."

            # ==========================================
            # လမ်းကြောင်း (၃): UI အတည်ပြုပြီးနောက် Backend ဆက်ရေးခြင်း
            # ==========================================
            elif command == "build_backend":
                logger.info("👨‍💻 STAGE 4: Building Backend...")
                coder_agent = JarvisAgent(role="coder")
                c_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'coder.md')
                if os.path.exists(c_prompt_path):
                    with open(c_prompt_path, 'r', encoding='utf-8') as f:
                        coder_agent.brain.system_instruction = f.read()
                        
                c_msg = f"PROJECT: {project_name}\nThe UI is LOCKED. Read 'final_blueprint.md' and the UI files. Now, build the REAL backend APIs, database logic, and connect them to the UI."
                coder_result = await coder_agent.chat(c_msg, user_id=999999)
                
                logger.info("🔐 STAGE 5: Checking .env for missing credentials...")
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
                    hitl_msg = f"✅ Backend Completed!\n\n[LEAD DEVELOPER REPORT]:\n{coder_result}\n\n"
                    hitl_msg += f"🛑 HUMAN-IN-THE-LOOP REQUIRED: The project needs these API Keys in `.env`: **{', '.join(missing_keys)}**.\n\n"
                    hitl_msg += f"👉 Tell the Sir to provide the keys here. Once provided, update the .env and run QA Testing."
                    return hitl_msg
                else:
                    return f"✅ Backend Completed!\n\n[LEAD DEVELOPER REPORT]:\n{coder_result}\n\n(Note: No missing keys. You can now automatically run QA Testing.)"

        except Exception as e:
            logger.error(f"Manager Pipeline Error: {e}")
            return f"❌ SE Team Pipeline encountered an error: {str(e)}"