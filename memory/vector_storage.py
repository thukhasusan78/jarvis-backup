import os
import logging
from datetime import datetime
from config import Config

# Vector DB အတွက် လိုအပ်သော Library များ
try:
    import lancedb
    from lancedb.pydantic import LanceModel, Vector
    from lancedb.embeddings import get_registry
except ImportError:
    lancedb = None

logger = logging.getLogger("JARVIS_VECTOR_STORAGE")

# အကယ်၍ Library များ install လုပ်ပြီးသားဆိုလျှင်
if lancedb:
    # စာသားတွေကို Vector (ဂဏန်း) အဖြစ်ပြောင်းပေးမည့် AI Model လေးကို ခေါ်မယ်
    embed_fn = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")

    # Database ထဲမှာ သိမ်းမယ့် ပုံစံ (Schema)
    class KnowledgeSchema(LanceModel):
        id: str
        category: str           # "Skill" (သို့) "Mistake" (သို့) "Fact"
        task_or_query: str = embed_fn.SourceField()  # ဒီနေရာမှာ ရှိတဲ့စာသားကို AI က နားလည်အောင် Vector ပြောင်းမယ်
        solution: str           # ဖြေရှင်းနည်း (သို့) အချက်အလက်
        code_snippet: str       # Code တွေပါရင် မှတ်ထားဖို့
        timestamp: str
        vector: Vector(embed_fn.ndims()) = embed_fn.VectorField()

class VectorStorage:
    def __init__(self):
        self.db_path = Config.VECTOR_DB_PATH
        self.table_name = "jarvis_knowledge"
        self.table = None
        
        if lancedb:
            self._init_db()
        else:
            logger.warning("⚠️ LanceDB မရှိပါ။ 'pip install lancedb sentence-transformers' ကို Run ပါ။")

    def _init_db(self):
        try:
            os.makedirs(self.db_path, exist_ok=True)
            self.db = lancedb.connect(self.db_path)
            
            # Table ရှိပြီးသားလား စစ်မယ်၊ မရှိရင် အသစ်ဆောက်မယ်
            if self.table_name not in self.db.table_names():
                self.table = self.db.create_table(self.table_name, schema=KnowledgeSchema)
                logger.info("✅ Vector Storage (Layer 2 - LanceDB) Initialized.")
            else:
                self.table = self.db.open_table(self.table_name)
                logger.info("✅ Vector Storage (Layer 2 - LanceDB) Connected.")
        except Exception as e:
            logger.error(f"❌ Vector DB Init Error: {e}")

    # ==========================================
    # အချက်အလက်နှင့် အတွေ့အကြုံများကို သိမ်းဆည်းခြင်း
    # ==========================================
    def save_knowledge(self, category: str, task: str, solution: str, code_snippet: str = ""):
        """
        category: "Skill" (ပြဿနာရှင်းနည်း), "Mistake" (အမှားများ), "Fact" (အချက်အလက်)
        """
        if not self.table: return False
        
        try:
            import uuid
            data = [{
                "id": uuid.uuid4().hex,
                "category": category,
                "task_or_query": task,
                "solution": solution,
                "code_snippet": code_snippet,
                "timestamp": datetime.datetime.now(Config.TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            }]
            self.table.add(data)
            return True
        except Exception as e:
            logger.error(f"Save Vector Error: {e}")
            return False

    # ==========================================
    # ပြဿနာကြုံလာလျှင် အရင်က အတွေ့အကြုံများထဲမှ ပြန်ရှာခြင်း
    # ==========================================
    def search_knowledge(self, query: str, limit: int = 3):
        """Jarvis ပြဿနာတစ်ခု ကြုံလာတိုင်း ဒီမှာ အရင်လာရှာမယ်"""
        if not self.table: return ""
        
        try:
            # AI က Query ရဲ့ အဓိပ္ပါယ်ကို နားလည်ပြီး အနီးစပ်ဆုံး တူတဲ့ဟာကို ရှာပေးမယ်
            results = self.table.search(query).limit(limit).to_list()
            
            if not results:
                return ""
            
            memory_text = "🧠 [JARVIS PAST EXPERIENCE & KNOWLEDGE]:\n"
            for res in results:
                # _distance က နည်းလေ ပိုတူလေပဲ (1.2 ထက်နည်းမှ ယူမယ် - မဆိုင်တာတွေ မပါအောင်)
                if res.get('_distance', 1.0) < 1.2:  
                    cat = res['category']
                    task = res['task_or_query']
                    sol = res['solution']
                    code = res['code_snippet']
                    
                    memory_text += f"\n[{cat}] Situation/Query: {task}\nAction/Fact: {sol}\n"
                    if code:
                        memory_text += f"Code Snippet:\n```\n{code}\n```\n"
                        
            return memory_text.strip()
        except Exception as e:
            logger.error(f"Search Vector Error: {e}")
            return ""

vector_storage = VectorStorage()