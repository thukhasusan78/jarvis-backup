import os
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger("JARVIS_VECTOR_STORAGE")

# 1. Library များကို ခေါ်ယူခြင်း
try:
    import lancedb
    from lancedb.pydantic import LanceModel, Vector
    from lancedb.embeddings import get_registry
except ImportError as e:
    lancedb = None
    print(f"❌ Library Error: lancedb မရှိပါ။ ({e})")

KnowledgeSchema = None
embed_fn = None

# 2. Schema ကို ကြိုတင် ပြင်ဆင်ခြင်း
if lancedb:
    try:
        embed_fn = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")
        
        class _Schema(LanceModel):
            id: str
            category: str           
            search_text: str = embed_fn.SourceField()  # အကုန်ပေါင်းမှတ်မည့် Field
            task_or_query: str
            solution: str           
            code_snippet: str       
            timestamp: str
            vector: Vector(384) = embed_fn.VectorField() 
        KnowledgeSchema = _Schema
    except Exception as e:
        print(f"❌ Embedding Load Error: {e}")

# 3. Storage Class
class VectorStorage:
    def __init__(self):
        self.db_path = os.path.abspath(Config.VECTOR_DB_PATH)
        self.table_name = "jarvis_knowledge_v3" # Schema အသစ်မို့ Table နာမည်ပြောင်းထားသည်
        self.table = None
        
        if lancedb and KnowledgeSchema:
            self._init_db()
        else:
            print("⚠️ Vector DB ကို ပိတ်ထားပါသည်။")

    def _init_db(self):
        try:
            os.makedirs(self.db_path, exist_ok=True)
            self.db = lancedb.connect(self.db_path)
            
            if self.table_name not in self.db.table_names():
                self.table = self.db.create_table(self.table_name, schema=KnowledgeSchema)
                print(f"✅ Vector Storage Initialized at: {self.db_path}")
            else:
                self.table = self.db.open_table(self.table_name)
                print(f"✅ Vector Storage Connected at: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Vector DB Init Error: {e}")
            return False

    def save_knowledge(self, category: str, task: str, solution: str, code_snippet: str = ""):
        if self.table is None:
            if lancedb and KnowledgeSchema:
                self._init_db()
            
        if self.table is None:
            print("❌ Save Error: Vector DB သို့ ချိတ်ဆက်၍ မရပါ။")
            return False
        
        try:
            import uuid
            # Problem ရော Solution ပါ ပေါင်းထည့်မည် (Search လုပ်ရ လွယ်အောင်)
            combined_text = f"Problem: {task}\nSolution: {solution}\nCode: {code_snippet}"
            
            data = [{
                "id": uuid.uuid4().hex,
                "category": category,
                "search_text": combined_text,
                "task_or_query": task,
                "solution": solution,
                "code_snippet": code_snippet,
                "timestamp": datetime.now(Config.TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            }]
            self.table.add(data)
            print(f"✅ Data successfully saved to Vector DB: [{category}]")
            return True
        except Exception as e:
            print(f"❌ Save Vector Error: {e}")
            return False

    def search_knowledge(self, query: str, limit: int = 3):
        if self.table is None:
            if lancedb and KnowledgeSchema:
                self._init_db()
        
        if self.table is None: 
            return ""
        
        try:
            results = self.table.search(query).limit(limit).to_list()
            if not results: return ""
            
            memory_text = "🧠 [JARVIS PAST EXPERIENCE & KNOWLEDGE]:\n"
            found_relevant = False
            
            for res in results:
                distance = res.get('_distance', 1.0)
                # 🔥 TONY STARK FIX: Distance ၁.၁ ထက်ငယ်မှ (တကယ်ဆိုင်မှ) ယူမည်။ 
                # (မဆိုင်တာတွေ ဆွဲမထုတ်လာအောင် တားထားခြင်း)
                if distance < 1.1:  
                    found_relevant = True
                    cat = res['category']
                    task = res['task_or_query']
                    sol = res['solution']
                    code = res['code_snippet']
                    
                    memory_text += f"\n[{cat}] Situation/Query: {task}\nAction/Fact: {sol}\n"
                    if code: memory_text += f"Code Snippet:\n```\n{code}\n```\n"
            
            # တကယ်ဆိုင်တဲ့ အချက်အလက် မတွေ့ရင် ဘာမှမပို့ဘူး
            if not found_relevant:
                return ""
                        
            return memory_text.strip()
        except Exception as e:
            print(f"❌ Search Vector Error: {e}")
            return ""

    def delete_knowledge(self, search_query: str):
        if self.table is None: return False
        try:
            results = self.table.search(search_query).limit(1).to_list()
            if results and results[0].get('_distance', 1.0) < 1.1:
                target_id = results[0]['id']
                self.table.delete(f"id = '{target_id}'")
                print(f"🗑️ Knowledge deleted successfully for: {search_query}")
                return True
            return False
        except Exception as e:
            print(f"❌ Delete Vector Error: {e}")
            return False        

vector_storage = VectorStorage()