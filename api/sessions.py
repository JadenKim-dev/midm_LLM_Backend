from fastapi import APIRouter, HTTPException, status
from typing import Optional
from models.schemas import SessionCreate, SessionResponse, MessagesHistoryResponse
from services.session_service import session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(session_data: Optional[SessionCreate] = None):
    """새 세션 생성"""
    try:
        metadata = session_data.metadata if session_data else {}
        session = await session_service.create_session(metadata)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """세션 정보 조회"""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    """세션 삭제 (메시지 포함)"""
    success = await session_service.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

@router.get("/{session_id}/messages", response_model=MessagesHistoryResponse)
async def get_session_messages(session_id: str, limit: Optional[int] = None):
    """세션의 메시지 히스토리 조회"""
    messages = await session_service.get_session_messages(session_id, limit)
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return MessagesHistoryResponse(
        session_id=session_id,
        messages=messages,
        total_count=len(messages)
    )