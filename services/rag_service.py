from typing import List, Dict, Tuple
from config import settings
from services.embedding_service import embedding_service
from services.vector_service import vector_service


class RAGService:
    def __init__(self):
        pass
    
    async def search_relevant_documents(
        self, 
        query: str, 
        session_id: str = None,
        top_k: int = None
    ) -> Tuple[List[str], List[float], List[Dict]]:
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K
        
        query_embedding = await embedding_service.generate_single_embedding(query)
        
        where_filter = None
        if session_id:
            where_filter = {"session_id": session_id}
        
        documents, similarities, metadatas = await vector_service.search_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where_filter
        )
        
        return documents, similarities, metadatas
    
    async def prepare_context(
        self, 
        query: str, 
        session_id: str = None,
        top_k: int = None
    ) -> List[str]:
        documents, similarities, metadatas = await self.search_relevant_documents(
            query=query,
            session_id=session_id,
            top_k=top_k
        )
        
        if not documents:
            return []
        
        context_docs = []
        for doc, metadata in zip(documents, metadatas):
            document_title = metadata.get('document_title', 'Unknown Document')
            context_docs.append(f"[{document_title}]\n{doc}")
        
        return context_docs
    
    async def get_rag_response_data(
        self,
        query: str,
        session_id: str = None,
        top_k: int = None
    ) -> Dict:
        context_docs = await self.prepare_context(
            query=query,
            session_id=session_id,
            top_k=top_k
        )
        
        return {
            "context": context_docs,
            "has_context": len(context_docs) > 0,
            "context_count": len(context_docs)
        }

rag_service = RAGService()