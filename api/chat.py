from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, ChatResponse
from services.chat_service import chat_service
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    try:
        response = await chat_service.process_chat_request(
            session_id=request.session_id,
            user_message=request.message,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            do_sample=request.do_sample,
            use_rag=request.use_rag,
            top_k=request.top_k
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
    async def generate_stream():
        try:
            async for chunk in chat_service.process_chat_stream(
                session_id=request.session_id,
                user_message=request.message,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                do_sample=request.do_sample,
                use_rag=request.use_rag,
                top_k=request.top_k
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except ValueError as e:
            error_chunk = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
        except Exception as e:
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