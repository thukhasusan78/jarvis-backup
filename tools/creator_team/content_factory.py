import os
import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from memory.memory_controller import memory_controller

logger = logging.getLogger("JARVIS_CONTENT_FACTORY")

class ContentFactoryTool(BaseTool):
    """
    Orchestrates the entire Content Creation Pipeline deterministically.
    Research -> Write Draft -> Save to Pending -> Request Approval.
    """
    name = "run_content_factory"
    description = "Run the automated content pipeline. It assigns tasks to 'deep_researcher' and 'content_writer' agents, saves the draft, and returns it for user approval."
    owner_role = ["ceo", "sysadmin"]

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "topic": types.Schema(
                type=types.Type.STRING,
                description="The exact news topic or keyword to draft content for (e.g., 'Latest AI news March 2026')."
            ),
            "persona_name": types.Schema(
                type=types.Type.STRING,
                description="The name of the persona to use for writing (e.g., 'Tech_Blogger')."
            )
        }

    def get_required(self) -> List[str]:
        return ["topic", "persona_name"]

    async def execute(self, **kwargs) -> str:
        # Agent တွေကို စက်ရုံထဲ လှမ်းခေါ်မည်
        from core.agent import JarvisAgent
        
        topic = kwargs.get("topic")
        persona_name = kwargs.get("persona_name")
        
        logger.info(f"🏭 Starting Content Factory Pipeline for: {topic}")

        try:
            # ၁။ PERSONA ပုံစံကို ရှာဖွေခြင်း
            persona_data = memory_controller.search_knowledge(f"Persona: {persona_name}")
            if not persona_data:
                persona_data = "Use a professional, engaging, and highly energetic tech-focused tone."

            # ၂။ DEEP RESEARCHER ကို သတင်းရှာခိုင်းခြင်း (Prompt အပြည့်အဝဖြင့်)
            logger.info("🏭 Step 1: Delegating to Deep Researcher Agent...")
            researcher = JarvisAgent(role="deep_researcher")
            
            r_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'deep_researcher.md')
            if os.path.exists(r_prompt_path):
                with open(r_prompt_path, 'r', encoding='utf-8') as f:
                    researcher.brain.system_instruction = f.read()
            
            r_msg = f"MISSION: Do a parallel deep search on the topic '{topic}'. Find facts, public opinions, and controversies. Return the full formatted Research Brief."
            research_result = await researcher.chat(r_msg, user_id=999999)

            # ၃။ CONTENT WRITER ကို ဇာတ်ညွှန်း ပြောင်းရေးခိုင်းခြင်း
            logger.info("🏭 Step 2: Delegating to Content Writer Agent...")
            writer = JarvisAgent(role="content_writer")
            
            w_prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'content_writer.md')
            if os.path.exists(w_prompt_path):
                with open(w_prompt_path, 'r', encoding='utf-8') as f:
                    writer.brain.system_instruction = f.read()
            
            w_msg = f"""
            MISSION: Write a highly engaging TELEGRAM POST based ONLY on this research brief.
            
            [WRITING STYLE / PERSONA]:
            {persona_data}
            
            [RESEARCH BRIEF]:
            {research_result}
            
            CRITICAL COMMAND: Output ONLY the final raw Telegram Post. DO NOT include conversational text like "Here is the post" or "I have written it". Just the content.
            """
            draft_content = await writer.chat(w_msg, user_id=999999)

            # ၄။ ယာယီဖိုင်အဖြစ် သိမ်းဆည်းခြင်း (Pending Draft)
            draft_dir = os.path.abspath(os.path.join("workspace", "drafts"))
            os.makedirs(draft_dir, exist_ok=True)
            draft_path = os.path.join(draft_dir, "pending_post.txt")
            
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(draft_content.strip())
                
            logger.info("🏭 Step 3: Draft saved to pending_post.txt")

            # ၅။ CEO အား အတင်းအကျပ် စည်းကမ်းထုတ်၍ ဆရာ့ထံ ပြန်ပို့ခိုင်းခြင်း
            success_message = (
                f"**[DRAFT READY FOR APPROVAL]**\n\n"
                f"========================\n"
                f"{draft_content.strip()}\n"
                f"========================\n\n"
                f"🚨 CRITICAL INSTRUCTION FOR CEO (JARVIS): \n"
                f"1. DO NOT summarize the draft above. \n"
                f"2. You MUST output the exact draft text to the Sir word-for-word. \n"
                f"3. Tell the Sir: 'ဆရာ၊ ဆောင်းပါး ရေးပြီးပါပြီ။ ဖတ်ကြည့်ပြီး သဘောကျရင် 'တင်လိုက်တော့' လို့ အမိန့်ပေးပါခင်ဗျာ။'"
            )
            return success_message

        except Exception as e:
            logger.error(f"Content Factory Error: {e}")
            return f"❌ Content Factory Pipeline Error: {str(e)}"