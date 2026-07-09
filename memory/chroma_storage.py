import os
import logging
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from config import Config
import uuid

logger = logging.getLogger("CHROMA_STORAGE")

class UnifiedChromaStorage:
    def __init__(self):
        os.makedirs(Config.CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        
        # System Environment ထဲမှာ Key ကို အရင် ကြေညာပေးမည် (Version 0.6.0 Fix)
        api_key = Config.API_KEYS[0] if Config.API_KEYS else os.getenv("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            
        self._doc_embedder = embedding_functions.GoogleGeminiEmbeddingFunction(
            model_name=Config.EMBEDDING_MODEL, task_type="RETRIEVAL_DOCUMENT"
        )
        self._query_embedder = embedding_functions.GoogleGeminiEmbeddingFunction(
            model_name=Config.EMBEDDING_MODEL, task_type="RETRIEVAL_QUERY"
        )
        
        # 1. Secretary အတွက် Collection
        self.business_collection = self.client.get_or_create_collection(
            name=Config.CHROMA_BUSINESS_COLLECTION,
            embedding_function=self._doc_embedder,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 2. CEO Agent အတွက် Collection
        self.knowledge_collection = self.client.get_or_create_collection(
            name=Config.CHROMA_KNOWLEDGE_COLLECTION,
            embedding_function=self._doc_embedder,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("🟢 Unified ChromaDB (Business & Knowledge) Initialized.")

    # ==========================================
    # SECRETARY RAG (Business Facts)
    # ==========================================
    def upsert_fact(self, category: str, fact: str, source: str = "admin") -> bool:
        try:
            self.business_collection.upsert(
                ids=[category],
                documents=[fact],
                metadatas=[{"category": category, "source": source}]
            )
            return True
        except Exception as e:
            logger.error(f"ChromaDB Upsert Error: {e}")
            return False

    def search_facts(self, query: str, limit: int = None) -> dict:
        if limit is None: limit = Config.CHROMA_TOP_K
        try:
            query_embedding = self._query_embedder([query])
            results = self.business_collection.query(
                query_embeddings=query_embedding, n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            filtered = {"documents": [[]], "metadatas": [[]]}
            if results and results["distances"] and results["distances"][0]:
                for i, dist in enumerate(results["distances"][0]):
                    if dist <= Config.CHROMA_DISTANCE_THRESHOLD:
                        filtered["documents"][0].append(results["documents"][0][i])
                        filtered["metadatas"][0].append(results["metadatas"][0][i])
            return filtered
        except Exception as e:
            logger.error(f"ChromaDB Query Error: {e}")
            return {}

    # ==========================================
    # CEO KNOWLEDGE (Replaced LanceDB)
    # ==========================================
    def save_knowledge(self, category: str, task: str, solution: str, code_snippet: str = "") -> bool:
        try:
            doc_id = uuid.uuid4().hex
            document_text = f"Task: {task}\nSolution: {solution}\nCode: {code_snippet}"
            self.knowledge_collection.add(
                ids=[doc_id],
                documents=[document_text],
                metadatas=[{"category": category, "task": task}]
            )
            return True
        except Exception as e:
            logger.error(f"CEO Knowledge Save Error: {e}")
            return False

    def search_knowledge(self, query: str, limit: int = 3) -> str:
        try:
            query_embedding = self._query_embedder([query])
            results = self.knowledge_collection.query(
                query_embeddings=query_embedding, n_results=limit,
                include=["documents", "distances"]
            )
            
            knowledge_texts = []
            if results and results["distances"] and results["distances"][0]:
                for i, dist in enumerate(results["distances"][0]):
                    if dist <= Config.CHROMA_DISTANCE_THRESHOLD:
                        knowledge_texts.append(results["documents"][0][i])
                        
            return "\n\n---\n\n".join(knowledge_texts) if knowledge_texts else "No relevant knowledge found."
        except Exception as e:
            return f"Search Error: {e}"

    def delete_knowledge(self, query: str) -> bool:
        """CEO Agent မှ မှားယွင်းသော Knowledge များကို ပြန်ဖျက်ရန်"""
        try:
            # ဖြတ်ချင်တဲ့ အကြောင်းအရာကို အရင်ရှာပြီး သူရဲ့ ID ကို ယူမည်
            query_embedding = self._query_embedder([query])
            results = self.knowledge_collection.query(
                query_embeddings=query_embedding, n_results=1
            )
            
            # တွေ့တယ်ဆိုရင် အဲ့ဒီ ID ကို ဖျက်မည်
            if results and results["ids"] and results["ids"][0]:
                doc_id = results["ids"][0][0]
                self.knowledge_collection.delete(ids=[doc_id])
                logger.info(f"🗑️ Deleted knowledge ID: {doc_id} based on query: {query}")
                return True
            return False
        except Exception as e:
            logger.error(f"CEO Knowledge Delete Error: {e}")
            return False        

chroma_storage = UnifiedChromaStorage()