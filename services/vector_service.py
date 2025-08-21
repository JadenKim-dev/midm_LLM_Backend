import chromadb
from chromadb.config import Settings as ChromaSettings
import uuid
from typing import List, Dict, Optional, Tuple
from config import settings


class VectorService:
    def __init__(self):
        self.client = None
        self.collection = None

    async def initialize(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

    async def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        if not self.collection:
            await self.initialize()

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        return ids

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = None,
        where: Optional[Dict] = None
    ) -> Tuple[List[str], List[float], List[Dict]]:
        if not self.collection:
            await self.initialize()

        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )

        documents = results['documents'][0] if results['documents'] else []
        distances = results['distances'][0] if results['distances'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []

        # 거리를 유사도로 변환 (cosine distance -> similarity)
        similarities = [1 - distance for distance in distances]

        # 최소 유사도 임계값 필터링
        filtered_results = []
        for doc, sim, meta in zip(documents, similarities, metadatas):
            if sim >= settings.MIN_SIMILARITY_SCORE:
                filtered_results.append((doc, sim, meta))

        if not filtered_results:
            return [], [], []

        docs, sims, metas = zip(*filtered_results)
        return list(docs), list(sims), list(metas)

    async def delete_documents(self, ids: List[str]):
        if not self.collection:
            await self.initialize()

        self.collection.delete(ids=ids)

    async def get_collection_count(self) -> int:
        if not self.collection:
            await self.initialize()

        return self.collection.count()


vector_service = VectorService()
