from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from services.document_service import document_service
from services.embedding_service import embedding_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


# CREATE: 문서 업로드
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )

        file_content = await file.read()

        document_id, chunk_data = await document_service.process_file(
            file_content=file_content,
            filename=file.filename,
            session_id=session_id
        )

        await document_service.save_chunks(chunk_data)

        embedding_ids = await embedding_service.update_chunk_embeddings(chunk_data)

        return {
            "document_id": document_id,
            "filename": file.filename,
            "chunks_count": len(chunk_data),
            "embedding_ids": embedding_ids
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


# READ: 문서 목록 조회
@router.get("")
async def get_session_documents(session_id: str):
    try:
        documents = await document_service.get_session_documents(session_id)
        return {
            "session_id": session_id,
            "documents": documents,
            "total_count": len(documents)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


# READ: 문서 청크 조회
@router.get("/{document_id}/chunks")
async def get_document_chunks(document_id: str):
    try:
        chunks = await document_service.get_document_chunks(document_id)
        return {
            "document_id": document_id,
            "chunks": chunks,
            "total_count": len(chunks)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chunks: {str(e)}"
        )


# DELETE: 문서 삭제
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str):
    try:
        success = await document_service.delete_document(document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )
