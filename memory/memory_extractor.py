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
        
        CRITICAL RULES:
        1. Extract ONLY NEW AND IMPORTANT information. Do NOT extract facts that were already established in previous turns.
        2. For 'skill', if J.A.R.V.I.S solved an error, searched the internet for a fix, or wrote important code, extract the EXACT code or command into the 'code_snippet' field.
        
        Classify them into:
        - 'profile': Facts about Sir (e.g., preferences, personal info, project names).
        - 'skill': Technical solutions, internet search results for errors, or learned experiences.
        
        If nothing NEW or IMPORTANT is found, return empty arrays.
        
        Conversation:
        Sir: {user_message}
        J.A.R.V.I.S: {ai_response}
        
        Respond ONLY with a valid JSON in this exact format, without markdown:
        {{
            "profile": [{{"key": "Category", "value": "The fact"}}],
            "skill": [{{"problem": "short description", "solution": "how it was solved", "code_snippet": "exact code/command here, or empty string"}}]
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