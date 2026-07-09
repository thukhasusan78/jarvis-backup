import os
import logging
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from config import Config

logger = logging.getLogger("CHROMA_STORAGE")

class BusinessFactStorage:
    def __init__(self):
        # 1. Ensure the directory exists
        os.makedirs(Config.CHROMA_BUSINESS_PATH, exist_ok=True)
        
        # 2. Initialize Persistent Client (Local Storage)
        self.client = chromadb.PersistentClient(path=Config.CHROMA_BUSINESS_PATH)
        
        # 3. Setup Official Gemini Embedding Function wrapper
        api_key = Config.API_KEYS[0] if Config.API_KEYS else os.getenv("GEMINI_API_KEY")
        
        self._doc_embedder = embedding_functions.GoogleGeminiEmbeddingFunction(
            api_key=api_key,
            model_name=Config.EMBEDDING_MODEL,
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        self._query_embedder = embedding_functions.GoogleGeminiEmbeddingFunction(
            api_key=api_key,
            model_name=Config.EMBEDDING_MODEL,
            task_type="RETRIEVAL_QUERY"
        )
        
        # 4. Get or Create Collection
        self.collection = self.client.get_or_create_collection(
            name=Config.CHROMA_COLLECTION,
            embedding_function=self._doc_embedder,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("🟢 ChromaDB (Business Facts) Initialized.")

    def upsert_fact(self, category: str, fact: str, source: str = "admin") -> bool:
        """Saves or updates a business fact using the category slug as the ID."""
        try:
            self.collection.upsert(
                ids=[category],
                documents=[fact],
                metadatas=[{"category": category, "source": source}]
            )
            return True
        except Exception as e:
            logger.error(f"❌ ChromaDB Upsert Error: {e}")
            return False

    def search_facts(self, query: str, limit: int = None) -> dict:
        """Retrieves relevant facts based on user query."""
        if limit is None: limit = Config.CHROMA_TOP_K
            
        try:
            query_embedding = self._query_embedder([query])
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            # Filter by Distance Threshold
            filtered_results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            threshold = Config.CHROMA_DISTANCE_THRESHOLD
            
            if results and results["distances"] and results["distances"][0]:
                for i, distance in enumerate(results["distances"][0]):
                    if distance <= threshold:
                        filtered_results["documents"][0].append(results["documents"][0][i])
                        filtered_results["metadatas"][0].append(results["metadatas"][0][i])
                        filtered_results["distances"][0].append(distance)
                        
            return filtered_results
        except Exception as e:
            logger.error(f"❌ ChromaDB Query Error: {e}")
            return {}

business_fact_storage = BusinessFactStorage()