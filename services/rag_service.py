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
    ) -> Tuple[List[str], List[Dict]]:
        documents, similarities, metadatas = await self.search_relevant_documents(
            query=query,
            session_id=session_id,
            top_k=top_k
        )

        if not documents:
            return [], []

        context_docs = []
        context_metadata = []
        for doc, similarity, metadata in zip(documents, similarities, metadatas):
            document_title = metadata.get('document_title', 'Unknown Document')
            document_id = metadata.get('document_id', '')

            context_docs.append(f"[{document_title}]\n{doc}")
            context_metadata.append({
                'document_id': document_id,
                'document_title': document_title,
                'chunk_content': doc,
                'similarity_score': similarity
            })

        return context_docs, context_metadata

    async def get_rag_response_data(
        self,
        query: str,
        session_id: str = None,
        top_k: int = None
    ) -> Tuple[List[str], List[Dict]]:
        context_docs, context_metadata = await self.prepare_context(
            query=query,
            session_id=session_id,
            top_k=top_k
        )

        return context_docs, context_metadata


rag_service = RAGService()
