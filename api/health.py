from fastapi import APIRouter
from datetime import datetime
from models.schemas import HealthResponse
from services.llm_client import llm_client
from models.database import db_manager

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 및 연결 상태 확인"""
    
    # LLM 서버 상태 확인
    llm_available = await llm_client.health_check()
    
    # 데이터베이스 연결 상태 확인
    db_connected = True
    try:
        await db_manager.get_connection()
    except Exception:
        db_connected = False
    
    return HealthResponse(
        status="healthy" if (llm_available and db_connected) else "degraded",
        timestamp=datetime.now(),
        llm_server_available=llm_available,
        database_connected=db_connected
    )