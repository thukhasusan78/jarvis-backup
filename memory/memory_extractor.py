import json
import logging
import asyncio
import re
from core.brain import JarvisBrain
from memory.memory_controller import memory_controller
from google import genai
from config import Config

logger = logging.getLogger("JARVIS_MEMORY_EXTRACTOR")

async def extract_and_store_memory(user_id: int, user_message: str, ai_response: str):
    """
    Fire and Forget Memory Engine (Contextual Deep Memory + Duplicate/Junk Prevention)
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
        4. 'admin_action': Extract ANY successful administrative, system, or configuration changes explicitly made by J.A.R.V.I.S (e.g., opening a port, restarting a service, modifying a system configuration).
        
        Conversation:
        Sir: {user_message}
        J.A.R.V.I.S: {ai_response}
        
        Respond ONLY with a valid JSON without markdown formatting:
        {{
            "profile": [{{"key": "Category", "value": "The fact"}}],
            "skill": [{{"problem": "Description of the exact error/bug faced", "solution": "How it was fixed", "code_snippet": "The exact fixed code or terminal command"}}],
            "admin_action": [{{"action": "What was executed/changed", "details": "Specific target like Port 8080, Nginx, or file path"}}]
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
        try:
            data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON Parse Error in Extractor: {e}. Raw: {clean_json[:200]}")
            return
        
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
                    memory_controller.save_knowledge("Skill", problem, solution, code_snippet)
                    logger.info(f"🧠 [Auto-Memory] Learned Skill Saved: {problem} (Includes Code: {'Yes' if code_snippet else 'No'})")

        # 3. Admin Actions (Contextual Deep Memory)
        if data.get("admin_action"):
            for action_item in data["admin_action"]:
                action = action_item.get("action", "")
                details = action_item.get("details", "")
                if action and details:
                    # အနာဂတ်မှာ ပြန်ရှာလို့ရအောင် Vector DB ထဲမှာ သိမ်းမည်
                    memory_controller.save_knowledge("Admin Action", f"System Change: {action}", details, "")
                    logger.info(f"🧠 [Auto-Memory] Contextual Action Saved: {action} -> {details}")

    except Exception as e:
        logger.error(f"Auto-Memory Extraction Failed: {e}")

async def extract_business_facts_from_admin_reply(chat_id: int, admin_message: str, recent_context: str = ""):
    """Extracts operational business facts directly from the Admin's chat messages."""
    
    prompt = f"""
    Analyze this Admin (Sir) reply in a customer DM thread.
    Extract ONLY operational business facts: pricing, stock, delivery times, payment rules, product specs.
    
    Output JSON ONLY: {{"business_fact": [{{"category": "snake_case_key", "fact": "full sentence"}}]}}
    
    Rules:
    - category must be stable snake_case (e.g. vpn_pricing, jammer_antenna_1_price)
    - If no business fact (e.g., just greetings or small talk), return {{"business_fact": []}}
    - Do NOT extract personal/chatty content
    
    Context:
    {recent_context}
    
    Admin Reply: {admin_message}
    """
    
    try:
        client = genai.Client(api_key=Config.get_next_api_key())
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not clean_json: return
            
        data = json.loads(clean_json.group(0))
        facts = data.get("business_fact", [])
        
        for item in facts:
            category = item.get("category")
            fact = item.get("fact")
            if category and fact:
                memory_controller.save_business_fact(category, fact, source="admin")
                logger.info(f"📈 Business Fact Updated: [{category}] {fact}")
                
    except Exception as e:
        logger.error(f"⚠️ Admin Fact Extraction Failed: {e}")        