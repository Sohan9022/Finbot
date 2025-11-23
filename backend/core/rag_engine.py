# """
# Simple RAG Engine for bill Q&A
# """

# import os
# import json
# from typing import Dict, List

# class BillRAGEngine:
#     """Simple RAG for financial Q&A"""
    
#     def __init__(self, user_id: int = None):
#         import streamlit as st
#         self.user_id = user_id or st.session_state.user['user_id']
#         self.data_file = f'models/user_{self.user_id}_rag.json'
#         self.documents = self.load_documents()
    
#     def load_documents(self) -> List[Dict]:
#         """Load stored documents"""
#         try:
#             if os.path.exists(self.data_file):
#                 with open(self.data_file, 'r') as f:
#                     return json.load(f)
#             return []
#         except:
#             return []
    
#     def add_document(self, text: str, metadata: Dict):
#         """Add document for Q&A"""
#         try:
#             doc = {
#                 'text': text,
#                 'metadata': metadata,
#                 'timestamp': str(metadata.get('transaction_date', ''))
#             }
            
#             self.documents.append(doc)
            
#             # Save
#             os.makedirs('models', exist_ok=True)
#             with open(self.data_file, 'w') as f:
#                 json.dump(self.documents[-1000:], f)  # Keep last 1000
            
#             return True
#         except Exception as e:
#             print(f"RAG error: {e}")
#             return False
    
#     def search(self, query: str, limit: int = 5) -> List[Dict]:
#         """Simple keyword search"""
#         query_lower = query.lower()
        
#         results = []
#         for doc in self.documents:
#             text_lower = doc['text'].lower()
            
#             # Simple keyword matching
#             if any(word in text_lower for word in query_lower.split()):
#                 results.append(doc)
        
#         return results[:limit]

"""
RAG Engine for bill Q&A (Optimized + Backend Safe)
- No Streamlit dependency
- Stores per-user documents
- Faster loading/saving
- Safer file handling
- Clean keyword search
"""

import os
import json
from typing import Dict, List, Optional


class BillRAGEngine:
    """Simple RAG engine for searching user's bill text"""

    def __init__(self, user_id: int):
        self.user_id = int(user_id)
        self.model_dir = "models"
        os.makedirs(self.model_dir, exist_ok=True)

        self.data_file = os.path.join(self.model_dir, f"user_{self.user_id}_rag.json")
        self.documents = self._load_documents()

    # --------------------------------------------------------
    # LOAD RAG DOCUMENTS
    # --------------------------------------------------------
    def _load_documents(self) -> List[Dict]:
        """Load stored documents for a user"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    # --------------------------------------------------------
    # ADD DOCUMENTS
    # --------------------------------------------------------
    def add_document(self, text: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add new bill text + metadata to user's RAG store
        metadata example:
            {
                "amount": 450,
                "transaction_date": "2024-02-12",
                "category": "Food"
            }
        """
        try:
            doc = {
                "text": text or "",
                "metadata": metadata or {},
                "timestamp": (metadata or {}).get("transaction_date", None)
            }

            self.documents.append(doc)

            # Keep only last 1500 documents (size control)
            trimmed = self.documents[-1500:]

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(trimmed, f, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"[RAG ERROR] Failed to save document: {e}")
            return False

    # --------------------------------------------------------
    # KEYWORD SEARCH
    # --------------------------------------------------------
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Very simple keyword search:
        - Splits query into words
        - Scores documents by number of matched keywords
        """

        if not query or not query.strip():
            return []

        keywords = query.lower().split()
        scored_docs = []

        for doc in self.documents:
            text = (doc.get("text") or "").lower()

            # score = number of matched keywords
            score = sum(1 for k in keywords if k in text)

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score (desc)
        scored_docs.sort(key=lambda x: -x[0])

        # Return only documents (not scores)
        return [d for _, d in scored_docs[:limit]]
