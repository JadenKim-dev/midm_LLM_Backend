import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
from models.database import db_manager
from models.schemas import ChatResponse, MessageResponse
from services.session_service import session_service
from services.llm_client import llm_client
from config import settings

class ChatService:
    
    async def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        token_usage: Optional[Dict] = None
    ) -> MessageResponse:
        """메시지를 데이터베이스에 저장"""
        message_id = str(uuid.uuid4())
        created_at = datetime.now()
        
        db = await db_manager.get_connection()
        
        await db.execute("""
            INSERT INTO messages (message_id, session_id, role, content, created_at, token_usage)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message_id, 
            session_id, 
            role, 
            content, 
            created_at,
            json.dumps(token_usage) if token_usage else None
        ))
        
        await db.commit()
        
        return MessageResponse(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=created_at,
            token_usage=token_usage
        )
    
    async def process_chat_request(
        self,
        session_id: str,
        user_message: str,
        max_new_tokens: int = None,
        temperature: float = None,
        do_sample: bool = None
    ) -> ChatResponse:
        """채팅 요청 처리 (일반)"""
        
        # 세션 존재 확인
        session = await session_service.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # 사용자 메시지 저장
        await self.save_message(session_id, "user", user_message)
        
        # 컨텍스트 메시지 조회
        context_messages = await session_service.get_recent_messages_for_context(session_id)
        
        # 시스템 메시지 추가 (첫 번째가 아닌 경우)
        if not any(msg["role"] == "system" for msg in context_messages):
            system_message = {
                "role": "system", 
                "content": "Mi:dm(믿:음)은 KT에서 개발한 AI 기반 어시스턴트이다."
            }
            context_messages.insert(0, system_message)
        
        # 기본값 설정
        if max_new_tokens is None:
            max_new_tokens = settings.DEFAULT_MAX_TOKENS
        if temperature is None:
            temperature = settings.DEFAULT_TEMPERATURE
        if do_sample is None:
            do_sample = True
        
        # LLM 서버에 요청
        llm_response = await llm_client.chat_completion(
            messages=context_messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=do_sample
        )
        
        # 어시스턴트 응답 저장
        assistant_message = await self.save_message(
            session_id=session_id,
            role="assistant",
            content=llm_response["response"],
            token_usage=llm_response.get("usage")
        )
        
        return ChatResponse(
            message_id=assistant_message.message_id,
            role="assistant",
            content=llm_response["response"],
            created_at=assistant_message.created_at,
            token_usage=llm_response.get("usage")
        )
    
    async def process_chat_stream(
        self,
        session_id: str,
        user_message: str,
        max_new_tokens: int = None,
        temperature: float = None,
        do_sample: bool = None
    ) -> AsyncGenerator[Dict, None]:
        """채팅 요청 처리 (스트리밍)"""
        
        # 세션 존재 확인
        session = await session_service.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # 사용자 메시지 저장
        await self.save_message(session_id, "user", user_message)
        
        # 컨텍스트 메시지 조회
        context_messages = await session_service.get_recent_messages_for_context(session_id)
        
        # 시스템 메시지 추가
        if not any(msg["role"] == "system" for msg in context_messages):
            system_message = {
                "role": "system", 
                "content": "Mi:dm(믿:음)은 KT에서 개발한 AI 기반 어시스턴트이다."
            }
            context_messages.insert(0, system_message)
        
        # 기본값 설정
        if max_new_tokens is None:
            max_new_tokens = settings.DEFAULT_MAX_TOKENS
        if temperature is None:
            temperature = settings.DEFAULT_TEMPERATURE  
        if do_sample is None:
            do_sample = True
        
        # 응답 수집을 위한 변수
        full_response = ""
        message_id = str(uuid.uuid4())
        
        try:
            # LLM 서버로부터 스트림 수신
            async for chunk in llm_client.chat_stream(
                messages=context_messages,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=do_sample
            ):
                # 클라이언트에게 청크 전달
                yield chunk
                
                # 응답 내용 수집
                if chunk.get("type") == "chunk":
                    full_response = chunk.get("accumulated", "")
                elif chunk.get("type") == "complete":
                    full_response = chunk.get("full_response", "")
            
            # 완전한 응답을 데이터베이스에 저장
            if full_response:
                await self.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response
                )
                
        except Exception as e:
            # 에러 발생시 에러 메시지 전달
            error_chunk = {
                "type": "error",
                "message": str(e)
            }
            yield error_chunk

# 전역 채팅 서비스 인스턴스
chat_service = ChatService()