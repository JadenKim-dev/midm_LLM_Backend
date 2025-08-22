from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Message(BaseModel):
    role: str = Field(..., description="메시지 역할 (system/user/assistant)")
    content: str = Field(..., description="메시지 내용")

class MessageCreate(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="사용자 메시지")

class MessageResponse(BaseModel):
    message_id: str = Field(..., description="메시지 ID")
    session_id: str = Field(..., description="세션 ID")
    role: str = Field(..., description="메시지 역할")
    content: str = Field(..., description="메시지 내용")
    created_at: datetime = Field(..., description="생성 시간")
    token_usage: Optional[Dict[str, Any]] = Field(None, description="토큰 사용량 정보")

class SessionCreate(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="세션 메타데이터")

class SessionResponse(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    created_at: datetime = Field(..., description="생성 시간")
    last_accessed: datetime = Field(..., description="마지막 접근 시간")
    metadata: Dict[str, Any] = Field(..., description="세션 메타데이터")

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="사용자 메시지")
    max_new_tokens: Optional[int] = Field(256, description="최대 생성 토큰 수")
    temperature: Optional[float] = Field(0.7, description="응답 생성 온도")
    do_sample: Optional[bool] = Field(True, description="샘플링 사용 여부")
    use_rag: Optional[bool] = Field(False, description="RAG 기능 사용 여부")
    top_k: Optional[int] = Field(None, description="RAG 검색 시 반환할 문서 수")

class RagContext(BaseModel):
    document_id: str = Field(..., description="문서 ID")
    document_title: str = Field(..., description="문서 제목")
    chunk_content: str = Field(..., description="사용된 청크 내용")
    similarity_score: float = Field(..., description="유사도 점수")

class ChatResponse(BaseModel):
    message_id: str = Field(..., description="메시지 ID") 
    role: str = Field("assistant", description="응답 역할")
    content: str = Field(..., description="응답 내용")
    created_at: datetime = Field(..., description="생성 시간")
    token_usage: Optional[Dict[str, Any]] = Field(None, description="토큰 사용량 정보")
    rag_context: Optional[List[RagContext]] = Field(None, description="RAG에서 사용된 문서 컨텍스트")

class MessagesHistoryResponse(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    messages: List[MessageResponse] = Field(..., description="메시지 히스토리")
    total_count: int = Field(..., description="전체 메시지 수")

class HealthResponse(BaseModel):
    status: str = Field("healthy", description="서버 상태")
    timestamp: datetime = Field(..., description="상태 확인 시간")
    llm_server_available: bool = Field(..., description="LLM 서버 연결 상태")
    database_connected: bool = Field(..., description="데이터베이스 연결 상태")

class PresentationCreate(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    topic: str = Field(..., description="발표 주제")
    theme: Optional[str] = Field("default", description="Marp 테마")

class PresentationResponse(BaseModel):
    presentation_id: str = Field(..., description="발표자료 ID")
    session_id: str = Field(..., description="세션 ID")
    title: str = Field(..., description="발표자료 제목")
    topic: str = Field(..., description="발표 주제")
    content: str = Field(..., description="상세 내용")
    marp_content: str = Field(..., description="Marp 형식 마크다운")
    theme: str = Field(..., description="Marp 테마")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

class PresentationListResponse(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    presentations: List[PresentationResponse] = Field(..., description="발표자료 목록")
    total_count: int = Field(..., description="전체 발표자료 수")

# 분석 관련 스키마
class AnalysisRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    topic: str = Field(..., description="분석할 주제")
    use_rag: Optional[bool] = Field(False, description="RAG 기능 사용 여부")
    top_k: Optional[int] = Field(5, description="RAG 검색 시 반환할 문서 수")

class AnalysisResponse(BaseModel):
    analysis_id: str = Field(..., description="분석 ID")
    session_id: str = Field(..., description="세션 ID")
    topic: str = Field(..., description="분석 주제")
    content: str = Field(..., description="분석 내용")
    created_at: datetime = Field(..., description="생성 시간")

# PPT 변환 관련 스키마
class ConversionRequest(BaseModel):
    analysis_id: str = Field(..., description="분석 ID")
    theme: Optional[str] = Field("default", description="Marp 테마")

class ConversionResponse(BaseModel):
    presentation_id: str = Field(..., description="발표자료 ID")
    analysis_id: str = Field(..., description="분석 ID")
    session_id: str = Field(..., description="세션 ID")
    title: str = Field(..., description="발표자료 제목")
    topic: str = Field(..., description="발표 주제")
    content: str = Field(..., description="원본 분석 내용")
    marp_content: str = Field(..., description="Marp 형식 마크다운")
    theme: str = Field(..., description="Marp 테마")
    created_at: datetime = Field(..., description="생성 시간")