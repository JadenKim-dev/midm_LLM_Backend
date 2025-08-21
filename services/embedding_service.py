import httpx
from typing import List, Dict
from config import settings
from services.vector_service import vector_service
from models.database import db_manager


class EmbeddingService:
    def __init__(self):
        self.llm_server_url = settings.LLM_SERVER_URL
        
    async def generate_embeddings(self, texts: List[str]) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_server_url}/embeddings",
                json={"texts": texts},
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    
    async def generate_single_embedding(self, text: str) -> List[float]:
        result = await self.generate_embeddings([text])
        return result["embeddings"][0]
    
    async def update_chunk_embeddings(self, chunk_data: List[Dict]) -> List[str]:
        if not chunk_data:
            return []
        
        texts = [chunk["content"] for chunk in chunk_data]
        
        try:
            embedding_result = await self.generate_embeddings(texts)
            embeddings = embedding_result["embeddings"]
            
            documents = []
            metadatas = []
            
            for chunk in chunk_data:
                documents.append(chunk["content"])
                metadatas.append(chunk["metadata"])
            
            embedding_ids = await vector_service.add_documents(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            db = await db_manager.get_connection()
            for chunk, embedding_id in zip(chunk_data, embedding_ids):
                await db.execute("""
                    UPDATE document_chunks 
                    SET embedding_id = ? 
                    WHERE chunk_id = ?
                """, (embedding_id, chunk["chunk_id"]))
            
            await db.commit()
            
            return embedding_ids
            
        except httpx.HTTPError as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to process embeddings: {str(e)}")

embedding_service = EmbeddingService()