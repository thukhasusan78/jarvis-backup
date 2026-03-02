import json
import logging
import asyncio
import re
from core.brain import JarvisBrain
from memory.memory_controller import memory_controller

logger = logging.getLogger("JARVIS_MEMORY_EXTRACTOR")

async def extract_and_store_memory(user_id: int, user_message: str, ai_response: str):
    """
    Fire and Forget Memory Engine (Upgraded with Code Snippet extraction & Duplicate prevention).
    """
    try:
        brain = JarvisBrain(role="ceo")
        
        prompt = f"""
        You are the Background Memory Extraction Engine for J.A.R.V.I.S.
        Analyze the following recent conversation.
        
        CRITICAL RULES FOR EXTRACTION (DO NOT IGNORE):
        1. 'profile': Extract ONLY NEW personal facts about Sir.
        2. 'skill': Extract ONLY HARD LESSONS. A "hard lesson" means J.A.R.V.I.S explicitly encountered an ERROR, failed, and then successfully found a workaround or fix (e.g., via Reflector or Web Search).
        3. DO NOT EXTRACT standard, successful tasks. If a task (like git push, reading a file, running a script) succeeded on the first try without any errors, IGNORE IT COMPLETELY. Do not save it as a skill.
        
        Conversation:
        Sir: {user_message}
        J.A.R.V.I.S: {ai_response}
        
        Respond ONLY with a valid JSON without markdown formatting:
        {{
            "profile": [{{"key": "Category", "value": "The fact"}}],
            "skill": [{{"problem": "Description of the exact error/bug faced", "solution": "How it was fixed", "code_snippet": "The exact fixed code or terminal command"}}]
        }}
        """
        
        ai_result = await asyncio.to_thread(brain.think, prompt)
        
        text_result = ""
        if isinstance(ai_result, str):
            text_result = ai_result
        elif hasattr(ai_result, 'candidates') and ai_result.candidates and ai_result.candidates[0].content.parts:
            text_result = ai_result.candidates[0].content.parts[0].text
            
        if not text_result: return
            
        clean_json = re.sub(r"```json\n|\n```|```", "", text_result).strip()
        data = json.loads(clean_json)
        
        # 1. Profile Facts (Short/Mid Term)
        if data.get("profile"):
            for item in data["profile"]:
                k = item.get("key", "Fact")
                v = item.get("value", "")
                if v:
                    memory_controller.save_user_fact(user_id, k, v)
                    logger.info(f"🧠 [Auto-Memory] Profile Fact Saved: {k} = {v}")
                
        # 2. Skills & Code Snippets (Deep Learning / Vector DB)
        if data.get("skill"):
            for skill in data["skill"]:
                problem = skill.get("problem", "")
                solution = skill.get("solution", "")
                code_snippet = skill.get("code_snippet", "")
                if problem and solution:
                    # code_snippet ပါ Vector DB ထဲ အလိုလို ရောက်သွားမည်
                    memory_controller.save_knowledge("Skill", problem, solution, code_snippet)
                    logger.info(f"🧠 [Auto-Memory] Learned Skill Saved: {problem} (Includes Code: {'Yes' if code_snippet else 'No'})")

    except Exception as e:
        logger.error(f"Auto-Memory Extraction Failed: {e}")