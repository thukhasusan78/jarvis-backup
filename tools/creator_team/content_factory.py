import os
import logging
import asyncio
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from core.brain import JarvisBrain
from tools.creator_team.parallel_research import ParallelResearchTool
from memory.memory_controller import memory_controller

logger = logging.getLogger("JARVIS_CONTENT_FACTORY")

class ContentFactoryTool(BaseTool):
    """
    Orchestrates the entire Content Creation Pipeline deterministically.
    Research -> Write Draft -> Save to Pending -> Request Approval.
    """
    name = "run_content_factory"
    description = "Run the automated content pipeline. It researches a topic, writes a highly engaging Telegram post using a persona, saves it as a draft, and returns it to the CEO for user approval."
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
        topic = kwargs.get("topic")
        persona_name = kwargs.get("persona_name")
        
        logger.info(f"🏭 Starting Content Factory Pipeline for: {topic}")

        try:
            # 1. PERSONA ရှာဖွေခြင်း
            persona_data = memory_controller.search_knowledge(f"Persona: {persona_name}")
            if not persona_data:
                persona_data = "Use a professional, engaging, and highly energetic tech-focused tone."

            # 2. DEEP RESEARCH လုပ်ခြင်း (Parallel Tool ကို တိုက်ရိုက်လှမ်းခေါ်မည်)
            logger.info("🏭 Step 1: Performing Deep Research...")
            researcher = ParallelResearchTool()
            research_data = await researcher.execute(query=topic)
            
            if "Error" in research_data or not research_data.strip():
                return "❌ Pipeline Failed during Research Phase. Please check Tavily API."

            # 3. WRITER AGENT ကို တိုက်ရိုက်ခိုင်းခြင်း (Code ထဲကနေ လှမ်းခေါ်မည်)
            logger.info("🏭 Step 2: Drafting Content with AI...")
            writer_brain = JarvisBrain(role="content_writer")
            
            draft_prompt = f"""
            You are the Expert Content Writer.
            Your task is to write a highly engaging TELEGRAM POST based ONLY on the research below.
            
            [WRITING STYLE / PERSONA]
            {persona_data}
            
            [FORMATTING RULES]
            - Follow strictly the "[FORMAT A: TELEGRAM POST]" rules from your system instructions.
            
            [RAW RESEARCH DATA]
            {research_data}
            """
            
            # Brain ကို Run မည်
            ai_result = await asyncio.to_thread(writer_brain.think, draft_prompt)
            
            draft_content = ""
            if isinstance(ai_result, str):
                draft_content = ai_result
            elif hasattr(ai_result, 'candidates') and ai_result.candidates:
                draft_content = ai_result.candidates[0].content.parts[0].text

            if not draft_content:
                return "❌ Pipeline Failed during Drafting Phase."

            # 4. ယာယီဖိုင်အဖြစ် သိမ်းဆည်းခြင်း (Pending Draft)
            draft_dir = os.path.abspath("workspace/drafts")
            os.makedirs(draft_dir, exist_ok=True)
            draft_path = os.path.join(draft_dir, "pending_post.txt")
            
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(draft_content.strip())
                
            logger.info("🏭 Step 3: Draft saved to pending_post.txt")

            # 5. ဆရာ့ဆီ Approval တောင်းရန် ပြန်ပို့ခြင်း
            success_message = (
                f"**[DRAFT READY FOR APPROVAL]**\n\n"
                f"ဆရာ၊ '{topic}' နဲ့ ပတ်သက်တဲ့ ဆောင်းပါးကို 'pending_post.txt' မှာ အဆင်သင့် ရေးသားသိမ်းဆည်းထားပါတယ်။\n\n"
                f"**[ဆောင်းပါး အကြမ်းဖျင်း]**\n"
                f"========================\n"
                f"{draft_content}\n"
                f"========================\n\n"
                f"အကယ်၍ သဘောကျတယ်ဆိုရင် **'တင်လိုက်တော့'** လို့ အမိန့်ပေးလိုက်ပါ။ `post_to_channel` နဲ့ ချက်ချင်း တင်ပေးပါမယ်။"
            )
            return success_message

        except Exception as e:
            logger.error(f"Content Factory Error: {e}")
            return f"❌ Content Factory Pipeline Error: {str(e)}"