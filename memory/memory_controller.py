import logging
import asyncio

# ရှေ့မှာရေးခဲ့တဲ့ အလွှာ (၂) ခုကို လှမ်းခေါ်မယ်
from memory.sql_storage import sql_storage
from memory.vector_storage import vector_storage

logger = logging.getLogger("JARVIS_MEMORY_CONTROLLER")

class MemoryController:
    """
    Agent နဲ့ Database တွေကြားက ပွဲစား (API Gateway)
    Agent က ဒီ Controller ကိုပဲ သိမယ်၊ နောက်ကွယ်မှာ ဘယ် DB ကို သွားရမလဲ သူပဲ ခွဲပေးမယ်။
    """
    def __init__(self):
        self.sql = sql_storage
        self.vector = vector_storage
        from memory.chroma_storage import business_fact_storage
        self.chroma = business_fact_storage
        logger.info("🧠 Memory Controller (Hybrid Core) Online.")

    # ==========================================
    # ၁။ Short-term Memory (စကားဝိုင်း မှတ်တမ်း) -> SQLite
    # ==========================================
    def add_chat_message(self, user_id: int, role: str, content: str):
        self.sql.add_message(user_id, role, content)

    def get_recent_chat(self, user_id: int, limit: int = 10) -> list:
        return self.sql.get_chat_history(user_id, limit)

    def clear_chat(self, user_id: int) -> str:
        return self.sql.clear_history(user_id)

    # ==========================================
    # ၂။ Permanent Facts (User Profile) -> SQLite
    # ==========================================
    def save_user_fact(self, user_id: int, key: str, value: str) -> bool:
        return self.sql.update_profile(user_id, key, value)

    def get_all_user_facts(self, user_id: int) -> str:
        return self.sql.get_user_profile(user_id)

    # ==========================================
    # ၃။ Ongoing Tasks (လုပ်လက်စ အလုပ်များ) -> SQLite
    # ==========================================
    def add_task(self, user_id: int, task_description: str) -> bool:
        return self.sql.add_ongoing_task(user_id, task_description)

    def get_tasks(self, user_id: int) -> str:
        return self.sql.get_ongoing_tasks(user_id)

    def remove_task(self, task_id: int) -> bool:
        return self.sql.remove_ongoing_task(task_id)

    # ==========================================
    # ၄။ Advanced Knowledge & Skills -> LanceDB (Vector)
    # ==========================================
    def save_knowledge(self, category: str, task: str, solution: str, code_snippet: str = "") -> bool:
        """category: 'Fact', 'Mistake', 'Skill'"""
        return self.vector.save_knowledge(category, task, solution, code_snippet)

    def search_knowledge(self, query: str, limit: int = 3) -> str:
        return self.vector.search_knowledge(query, limit)

    def delete_knowledge(self, query: str) -> bool:
        return self.vector.delete_knowledge(query)    

    # ==========================================
    # ၅။ Business Facts (Secretary RAG) -> ChromaDB
    # ==========================================
    def save_business_fact(self, category: str, fact: str, source: str = "admin") -> bool:
        return self.chroma.upsert_fact(category, fact, source)

    def search_business_facts(self, query: str, limit: int = 5) -> str:
        results = self.chroma.search_facts(query, limit)
        if not results: return ""
        
        formatted_facts = []
        for meta, doc in zip(results.get("metadatas", [[]])[0], results.get("documents", [[]])[0]):
            formatted_facts.append(f"- [{meta.get('category', 'fact')}] {doc}")
            
        return "\n".join(formatted_facts)    

# Singleton အနေနဲ့ ထုတ်ပေးထားမယ်
memory_controller = MemoryController()