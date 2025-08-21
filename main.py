from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from models.database import db_manager
from api import sessions, chat, health, documents
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행할 코드"""
    # Startup: 데이터베이스 연결 및 테이블 생성
    print("Starting Chatbot Backend Server...")
    try:
        await db_manager.connect()
        print("Database connected and tables created successfully!")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise
    
    yield
    
    # Shutdown: 데이터베이스 연결 해제
    print("Shutting down Chatbot Backend Server...")
    await db_manager.disconnect()
    print("Database disconnected.")

# FastAPI 앱 생성
app = FastAPI(
    title="Chatbot Backend API",
    description="LLM 서버와 통신하는 챗봇 백엔드 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(documents.router)

# 루트 엔드포인트
@app.get("/")
async def root():
    """API 정보 및 엔드포인트 목록"""
    return {
        "service": "Chatbot Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "sessions": {
                "create": "POST /api/sessions",
                "get": "GET /api/sessions/{session_id}",
                "delete": "DELETE /api/sessions/{session_id}",
                "messages": "GET /api/sessions/{session_id}/messages"
            },
            "chat": {
                "completion": "POST /api/chat",
                "stream": "POST /api/chat/stream"
            },
            "documents": {
                "upload": "POST /api/documents/upload",
                "list": "GET /api/documents?session_id={session_id}", 
                "delete": "DELETE /api/documents/{document_id}",
                "chunks": "GET /api/documents/{document_id}/chunks"
            },
            "health": "GET /api/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )