import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import db_manager
from models.schemas import SessionResponse, MessageResponse
from config import settings


class SessionService:

    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> SessionResponse:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        created_at = datetime.now()

        if metadata is None:
            metadata = {}

        db = await db_manager.get_connection()

        await db.execute("""
            INSERT INTO sessions (session_id, created_at, last_accessed, metadata)
            VALUES (?, ?, ?, ?)
        """, (session_id, created_at, created_at, json.dumps(metadata)))

        await db.commit()

        return SessionResponse(
            session_id=session_id,
            created_at=created_at,
            last_accessed=created_at,
            metadata=metadata
        )

    async def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """세션 조회"""
        db = await db_manager.get_connection()

        cursor = await db.execute("""
            SELECT session_id, created_at, last_accessed, metadata
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))

        row = await cursor.fetchone()
        if not row:
            return None

        await self._update_last_accessed(session_id)

        return SessionResponse(
            session_id=row[0],
            created_at=datetime.fromisoformat(row[1]),
            last_accessed=datetime.now(),
            metadata=json.loads(row[3]) if row[3] else {}
        )

    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제 (메시지 포함)"""
        db = await db_manager.get_connection()

        cursor = await db.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
        if not await cursor.fetchone():
            return False

        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        await db.commit()
        return True

    async def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> Optional[List[MessageResponse]]:
        """세션의 메시지 히스토리 조회"""
        if not await self._session_exists(session_id):
            return None

        db = await db_manager.get_connection()

        query = """
            SELECT message_id, session_id, role, content, created_at, token_usage
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
        """

        params = [session_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        messages = []
        for row in rows:
            messages.append(MessageResponse(
                message_id=row[0],
                session_id=row[1],
                role=row[2],
                content=row[3],
                created_at=datetime.fromisoformat(row[4]),
                token_usage=json.loads(row[5]) if row[5] else None
            ))

        return messages

    async def get_recent_messages_for_context(self, session_id: str, limit: int = None) -> List[Dict[str, str]]:
        """LLM 컨텍스트용 최근 메시지 조회"""
        if limit is None:
            limit = settings.MAX_CONTEXT_MESSAGES

        messages = await self.get_session_messages(session_id, limit)
        if not messages:
            return []

        messages.reverse()
        context_messages = []
        for msg in messages:
            context_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return context_messages

    async def cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리"""
        cutoff_time = datetime.now() - timedelta(hours=settings.SESSION_TIMEOUT_HOURS)

        db = await db_manager.get_connection()

        await db.execute("""
            DELETE FROM messages 
            WHERE session_id IN (
                SELECT session_id FROM sessions 
                WHERE last_accessed < ?
            )
        """, (cutoff_time,))

        cursor = await db.execute("""
            DELETE FROM sessions 
            WHERE last_accessed < ?
        """, (cutoff_time,))

        await db.commit()
        return cursor.rowcount

    async def _session_exists(self, session_id: str) -> bool:
        """세션 존재 여부 확인"""
        db = await db_manager.get_connection()
        cursor = await db.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
        return await cursor.fetchone() is not None

    async def _update_last_accessed(self, session_id: str):
        """세션의 마지막 접근 시간 업데이트"""
        db = await db_manager.get_connection()
        await db.execute("""
            UPDATE sessions 
            SET last_accessed = ? 
            WHERE session_id = ?
        """, (datetime.now(), session_id))
        await db.commit()


session_service = SessionService()
