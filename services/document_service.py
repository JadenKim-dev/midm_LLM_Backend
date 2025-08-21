import uuid
import json
import io
from datetime import datetime
from typing import List, Dict, Tuple
from pathlib import Path

import pypdf
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from models.database import db_manager
from config import settings
from services.vector_service import vector_service


class DocumentService:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.DEFAULT_CHUNK_SIZE,
            chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    async def process_file(
        self,
        file_content: bytes,
        filename: str,
        session_id: str
    ) -> Tuple[str, List[Dict]]:

        file_ext = Path(filename).suffix.lower()

        if file_ext == '.pdf':
            text = self._extract_pdf_text(file_content)
        elif file_ext == '.docx':
            text = self._extract_docx_text(file_content)
        elif file_ext == '.txt':
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = file_content.decode('euc-kr')
                except UnicodeDecodeError:
                    text = file_content.decode('cp949')
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        document_id = await self._save_document(
            session_id=session_id,
            title=filename,
            content=text,
            file_type=file_ext[1:]
        )

        chunks = self._chunk_text(text)

        chunk_data = []
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                'chunk_id': str(uuid.uuid4()),
                'document_id': document_id,
                'chunk_index': i,
                'content': chunk,
                'metadata': {
                    'document_title': filename,
                    'chunk_size': len(chunk),
                    'session_id': session_id
                }
            })

        return document_id, chunk_data

    def _extract_pdf_text(self, file_content: bytes) -> str:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = pypdf.PdfReader(pdf_file)

        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        return text.strip()

    def _extract_docx_text(self, file_content: bytes) -> str:
        docx_file = io.BytesIO(file_content)
        document = Document(docx_file)

        text = ""
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"

        return text.strip()

    def _chunk_text(self, text: str) -> List[str]:
        chunks = self.text_splitter.split_text(text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    async def _save_document(
        self,
        session_id: str,
        title: str,
        content: str,
        file_type: str
    ) -> str:
        document_id = str(uuid.uuid4())

        db = await db_manager.get_connection()
        await db.execute("""
            INSERT INTO documents (document_id, session_id, title, content, file_type, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            session_id,
            title,
            content,
            file_type,
            datetime.now(),
            json.dumps({'original_filename': title})
        ))
        await db.commit()

        return document_id

    async def save_chunks(self, chunks_data: List[Dict]):
        db = await db_manager.get_connection()

        for chunk_data in chunks_data:
            await db.execute("""
                INSERT INTO document_chunks (chunk_id, document_id, chunk_index, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                chunk_data['chunk_id'],
                chunk_data['document_id'],
                chunk_data['chunk_index'],
                chunk_data['content'],
                datetime.now()
            ))

        await db.commit()

    async def get_session_documents(self, session_id: str) -> List[Dict]:
        db = await db_manager.get_connection()

        cursor = await db.execute("""
            SELECT document_id, title, file_type, created_at, metadata
            FROM documents 
            WHERE session_id = ?
            ORDER BY created_at DESC
        """, (session_id,))

        rows = await cursor.fetchall()

        documents = []
        for row in rows:
            documents.append({
                'document_id': row[0],
                'title': row[1],
                'file_type': row[2],
                'created_at': row[3],
                'metadata': json.loads(row[4]) if row[4] else {}
            })

        return documents

    async def delete_document(self, document_id: str) -> bool:
        db = await db_manager.get_connection()

        cursor = await db.execute(
            "SELECT document_id FROM documents WHERE document_id = ?",
            (document_id,)
        )
        if not await cursor.fetchone():
            return False

        cursor = await db.execute(
            "SELECT embedding_id FROM document_chunks WHERE document_id = ? AND embedding_id IS NOT NULL",
            (document_id,)
        )
        embedding_ids = [row[0] for row in await cursor.fetchall()]

        if embedding_ids:
            await vector_service.delete_documents(embedding_ids)

        await db.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
        await db.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        await db.commit()

        return True

    async def get_document_chunks(self, document_id: str) -> List[Dict]:
        db = await db_manager.get_connection()

        cursor = await db.execute("""
            SELECT chunk_id, chunk_index, content, embedding_id, created_at
            FROM document_chunks 
            WHERE document_id = ?
            ORDER BY chunk_index
        """, (document_id,))

        rows = await cursor.fetchall()

        chunks = []
        for row in rows:
            chunks.append({
                'chunk_id': row[0],
                'chunk_index': row[1],
                'content': row[2],
                'embedding_id': row[3],
                'created_at': row[4]
            })

        return chunks


document_service = DocumentService()
