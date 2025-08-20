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
        
        session = await session_service.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        await self.save_message(session_id, "user", user_message)
        
        context_messages = await session_service.get_recent_messages_for_context(session_id)
        
        # 시스템 메시지 추가 (첫 번째가 아닌 경우)
        if not any(msg["role"] == "system" for msg in context_messages):
            system_message = {
                "role": "system", 
                "content": "Mi:dm(믿:음)은 KT에서 개발한 AI 기반 어시스턴트이다."
            }
            context_messages.insert(0, system_message)
        
        if max_new_tokens is None:
            max_new_tokens = settings.DEFAULT_MAX_TOKENS
        if temperature is None:
            temperature = settings.DEFAULT_TEMPERATURE
        if do_sample is None:
            do_sample = True
        
        llm_response = await llm_client.chat_completion(
            messages=context_messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=do_sample
        )
        
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
        token_count = 0
        
        try:
            yield {
                "type": "start",
                "message": "Stream started"
            }
            
            # LLM 서버로부터 스트림 수신
            async for chunk in llm_client.chat_stream(
                messages=context_messages,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=do_sample
            ):
                # 청크 타입별 처리
                if chunk.get("type") == "chunk":
                    token_content = chunk.get("content", "")
                    full_response += token_content
                    token_count += 1
                    
                    # 개별 토큰 전송
                    yield {
                        "type": "token",
                        "content": token_content,
                        "token_count": token_count
                    }
                    
                elif chunk.get("type") == "complete":
                    final_response = chunk.get("full_response", full_response)
                    if final_response and final_response != full_response:
                        full_response = final_response
                    
                    yield {
                        "type": "complete",
                        "total_tokens": token_count
                    }
                    
                elif chunk.get("type") == "error":
                    yield chunk
                    return
            
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