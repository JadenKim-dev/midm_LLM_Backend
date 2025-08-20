from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, ChatResponse
from services.chat_service import chat_service
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """일반 채팅 완성 요청"""
    try:
        response = await chat_service.process_chat_request(
            session_id=request.session_id,
            user_message=request.message,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            do_sample=request.do_sample
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """스트리밍 채팅 요청"""
    async def generate_stream():
        try:
            async for chunk in chat_service.process_chat_stream(
                session_id=request.session_id,
                user_message=request.message,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                do_sample=request.do_sample
            ):
                # SSE 형식으로 전송
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            # 스트림 완료 신호
            yield "data: [DONE]\n\n"
            
        except ValueError as e:
            # 세션 없음 등의 에러
            error_chunk = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
        except Exception as e:
            # 기타 서버 에러
            error_chunk = {
                "type": "error", 
                "message": f"Chat processing failed: {str(e)}"
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )