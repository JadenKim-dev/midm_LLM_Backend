from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import (
    PresentationCreate, PresentationResponse, PresentationListResponse,
    AnalysisRequest, AnalysisResponse, ConversionRequest, ConversionResponse
)
from services.presentation_service import presentation_service
import json
from datetime import datetime

router = APIRouter()


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)




@router.get("/{presentation_id}", response_model=PresentationResponse)
async def get_presentation(presentation_id: str):
    """발표자료 조회"""
    presentation = await presentation_service.get_presentation(presentation_id)
    if not presentation:
        raise HTTPException(status_code=404, detail="발표자료를 찾을 수 없습니다.")
    return presentation


@router.get("/list/{session_id}", response_model=PresentationListResponse)
async def list_presentations(session_id: str):
    """세션별 발표자료 목록 조회"""
    try:
        return await presentation_service.list_presentations(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"발표자료 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/analyze")
async def analyze_topic_stream(request: AnalysisRequest):
    """주제 분석 (스트리밍)"""
    try:
        async def stream_generator():
            async for chunk in presentation_service.analyze_topic_stream(request):
                # SSE 형식으로 데이터 전송
                yield f"data: {json.dumps(chunk, ensure_ascii=False, cls=DateTimeEncoder)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주제 분석 중 오류가 발생했습니다: {str(e)}")


@router.post("/convert")
async def convert_to_presentation_stream(request: ConversionRequest):
    """분석 내용을 발표자료로 변환 (스트리밍)"""
    try:
        async def stream_generator():
            async for chunk in presentation_service.convert_to_presentation_stream(request):
                # SSE 형식으로 데이터 전송
                yield f"data: {json.dumps(chunk, ensure_ascii=False, cls=DateTimeEncoder)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"발표자료 변환 중 오류가 발생했습니다: {str(e)}")


@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str):
    """분석 결과 조회"""
    analysis = await presentation_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    return analysis