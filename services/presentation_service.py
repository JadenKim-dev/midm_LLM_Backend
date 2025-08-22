import uuid
import json
from typing import List, Optional, AsyncGenerator, Dict
from datetime import datetime
from models.database import db_manager
from models.schemas import (
    PresentationCreate, PresentationResponse, PresentationListResponse,
    AnalysisRequest, AnalysisResponse, ConversionRequest, ConversionResponse
)
from services.llm_client import llm_client


class PresentationService:
    def __init__(self):
        self.analysis_prompt_template = """
당신은 전문적인 주제 분석 전문가입니다. 주어진 주제에 대해 상세하고 체계적인 분석을 제공해주세요.

주제: {topic}

**작성 가이드라인:**
- 한국어로 작성하되, 전문 용어는 필요시 영어 병기
- 구체적인 데이터와 사실 기반의 내용
- 논리적이고 체계적인 구성
- 실무진이 이해하기 쉬운 언어 사용
- 풍부한 예시와 구체적인 설명

주제에 대한 전문적이고 실용적인 분석을 제공해주세요.
"""


        self.marp_conversion_prompt = """
다음 발표 내용을 전문적인 Marp 형식의 마크다운으로 변환해주세요.

발표 내용:
{content}

**Marp 변환 규칙:**

1. **헤더 설정:**
   ```markdown
   ---
   marp: true
   theme: default
   paginate: true
   backgroundColor: #fff
   ---
   ```

2. **슬라이드 구성:**
   - 첫 번째 슬라이드: 타이틀 슬라이드 (중앙 정렬)
   - 두 번째 슬라이드: 목차/개요
   - 각 주요 섹션마다 새로운 슬라이드
   - 내용이 많은 섹션은 2-3개 슬라이드로 분할

3. **마크다운 문법:**
   - 슬라이드 구분: `---`
   - 제목: `# Title` (메인 제목), `## Subtitle` (소제목)
   - 불릿 포인트: `- 내용` 또는 `1. 내용`
   - 강조: **굵게**, *기울임*
   - 중앙 정렬: `<!-- fit -->`를 제목에 추가

4. **시각적 요소:**
   - 각 슬라이드에 적절한 제목
   - 내용을 3-5개 불릿 포인트로 구성
   - 중요한 키워드는 **강조 표시**
   - 숫자나 통계는 눈에 띄게 표시

5. **슬라이드 분량:**
   - 한 슬라이드당 3-7줄 내용
   - 텍스트가 많으면 여러 슬라이드로 분할
   - 마지막 슬라이드: 감사 인사 및 Q&A

완성된 Marp 마크다운만 출력해주세요. 추가 설명이나 주석은 포함하지 마세요.
"""

    async def analyze_topic_stream(self, request: AnalysisRequest) -> AsyncGenerator[Dict, None]:
        """주제 분석 (스트리밍)"""
        analysis_id = str(uuid.uuid4())
        
        try:
            # 1. 시작 알림
            yield {
                "type": "start",
                "message": "주제 분석을 시작합니다...",
                "analysis_id": analysis_id,
                "topic": request.topic
            }
            
            # 2. 분석 진행
            yield {
                "type": "progress",
                "step": "analysis",
                "message": f"'{request.topic}' 주제를 상세히 분석하고 있습니다..."
            }
            
            content = ""
            async for chunk in self._analyze_topic_stream(request.topic):
                if chunk.get("type") == "chunk":
                    content += chunk.get("content", "")
                    yield {
                        "type": "content_chunk",
                        "step": "analysis",
                        "content": chunk.get("content", ""),
                        "accumulated_content": content
                    }
                elif chunk.get("type") == "complete":
                    yield {
                        "type": "step_complete",
                        "step": "analysis",
                        "message": "주제 분석이 완료되었습니다."
                    }
            
            # 3. 데이터베이스 저장
            yield {
                "type": "progress",
                "step": "saving",
                "message": "분석 결과를 저장하고 있습니다..."
            }
            
            await self._save_analysis(
                analysis_id=analysis_id,
                session_id=request.session_id,
                topic=request.topic,
                content=content
            )
            
            yield {
                "type": "step_complete",
                "step": "saving",
                "message": "분석 결과 저장이 완료되었습니다."
            }
            
            # 4. 완료 알림
            analysis = await self.get_analysis(analysis_id)
            yield {
                "type": "complete",
                "message": "주제 분석이 완료되었습니다!",
                "analysis": analysis.dict(mode='json') if analysis else None
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "message": f"주제 분석 중 오류가 발생했습니다: {str(e)}"
            }

    async def convert_to_presentation_stream(self, request: ConversionRequest) -> AsyncGenerator[Dict, None]:
        """분석 내용을 발표자료로 변환 (스트리밍)"""
        presentation_id = str(uuid.uuid4())
        
        try:
            # 1. 분석 내용 조회
            analysis = await self.get_analysis(request.analysis_id)
            if not analysis:
                yield {
                    "type": "error",
                    "message": "분석 내용을 찾을 수 없습니다."
                }
                return
            
            title = f"{analysis.topic} 발표자료"
            
            # 2. 시작 알림
            yield {
                "type": "start",
                "message": "발표자료 변환을 시작합니다...",
                "presentation_id": presentation_id,
                "analysis_id": request.analysis_id,
                "topic": analysis.topic
            }
            
            # 3. Marp 변환 단계
            yield {
                "type": "progress",
                "step": "marp_conversion",
                "message": "분석 내용을 Marp 형식으로 변환하고 있습니다..."
            }
            
            marp_content = ""
            async for chunk in self._convert_to_marp_stream(analysis.content):
                if chunk.get("type") == "chunk":
                    marp_content += chunk.get("content", "")
                    yield {
                        "type": "marp_chunk",
                        "step": "marp_conversion",
                        "content": chunk.get("content", ""),
                        "accumulated_marp": marp_content
                    }
                elif chunk.get("type") == "complete":
                    yield {
                        "type": "step_complete",
                        "step": "marp_conversion",
                        "message": "Marp 형식 변환이 완료되었습니다."
                    }
            
            # 4. 데이터베이스 저장 단계
            yield {
                "type": "progress",
                "step": "saving",
                "message": "발표자료를 저장하고 있습니다..."
            }
            
            await self._save_presentation_with_analysis(
                presentation_id=presentation_id,
                analysis_id=request.analysis_id,
                session_id=analysis.session_id,
                title=title,
                topic=analysis.topic,
                content=analysis.content,
                marp_content=marp_content,
                theme=request.theme or "default"
            )
            
            yield {
                "type": "step_complete",
                "step": "saving",
                "message": "발표자료 저장이 완료되었습니다."
            }
            
            # 5. 완료 알림
            presentation = await self.get_presentation(presentation_id)
            yield {
                "type": "complete",
                "message": "발표자료 변환이 완료되었습니다!",
                "presentation": presentation.dict(mode='json') if presentation else None
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "message": f"발표자료 변환 중 오류가 발생했습니다: {str(e)}"
            }




    async def _convert_to_marp_stream(self, content: str) -> AsyncGenerator[Dict, None]:
        """상세 내용을 Marp 형식으로 변환 (스트리밍)"""
        messages = [
            {
                "role": "system",
                "content": "당신은 Marp 마크다운 변환 전문가입니다."
            },
            {
                "role": "user",
                "content": self.marp_conversion_prompt.format(content=content)
            }
        ]
        
        async for chunk in llm_client.chat_stream(
            messages=messages,
            max_new_tokens=2048,
            temperature=0.3,
            do_sample=True
        ):
            yield chunk


    async def _save_presentation(
        self, 
        presentation_id: str,
        session_id: str,
        title: str,
        topic: str,
        content: str,
        marp_content: str,
        theme: str
    ):
        """발표자료를 데이터베이스에 저장 (분석 없이 직접 생성된 경우)"""
        conn = await db_manager.get_connection()
        
        await conn.execute("""
            INSERT INTO presentations 
            (presentation_id, analysis_id, session_id, title, topic, content, marp_content, theme, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            presentation_id,
            None,  # analysis_id는 NULL
            session_id,
            title,
            topic,
            content,
            marp_content,
            theme,
            datetime.now(),
            datetime.now()
        ))
        
        await conn.commit()

    async def get_presentation(self, presentation_id: str) -> Optional[PresentationResponse]:
        """발표자료 조회"""
        conn = await db_manager.get_connection()
        
        async with conn.execute("""
            SELECT presentation_id, analysis_id, session_id, title, topic, content, marp_content, theme, created_at, updated_at
            FROM presentations 
            WHERE presentation_id = ?
        """, (presentation_id,)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return None
                
            return PresentationResponse(
                presentation_id=row[0],
                session_id=row[2],
                title=row[3],
                topic=row[4],
                content=row[5],
                marp_content=row[6],
                theme=row[7],
                created_at=datetime.fromisoformat(row[8]),
                updated_at=datetime.fromisoformat(row[9])
            )

    async def list_presentations(self, session_id: str) -> PresentationListResponse:
        """세션별 발표자료 목록 조회"""
        conn = await db_manager.get_connection()
        
        # 발표자료 목록 조회
        presentations = []
        async with conn.execute("""
            SELECT presentation_id, analysis_id, session_id, title, topic, content, marp_content, theme, created_at, updated_at
            FROM presentations 
            WHERE session_id = ?
            ORDER BY created_at DESC
        """, (session_id,)) as cursor:
            async for row in cursor:
                presentations.append(PresentationResponse(
                    presentation_id=row[0],
                    session_id=row[2],
                    title=row[3],
                    topic=row[4],
                    content=row[5],
                    marp_content=row[6],
                    theme=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9])
                ))
        
        # 전체 개수 조회
        async with conn.execute("""
            SELECT COUNT(*) FROM presentations WHERE session_id = ?
        """, (session_id,)) as cursor:
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0
        
        return PresentationListResponse(
            session_id=session_id,
            presentations=presentations,
            total_count=total_count
        )

    # 새로운 헬퍼 메서드들
    async def _analyze_topic_stream(self, topic: str) -> AsyncGenerator[Dict, None]:
        """주제 분석 (스트리밍)"""
        messages = [
            {
                "role": "system",
                "content": "당신은 전문적인 주제 분석 전문가입니다."
            },
            {
                "role": "user", 
                "content": self.analysis_prompt_template.format(topic=topic)
            }
        ]
        
        async for chunk in llm_client.chat_stream(
            messages=messages,
            max_new_tokens=2048,
            temperature=0.7,
            do_sample=True
        ):
            yield chunk

    async def _save_analysis(
        self, 
        analysis_id: str,
        session_id: str,
        topic: str,
        content: str
    ):
        """분석 결과를 데이터베이스에 저장"""
        conn = await db_manager.get_connection()
        
        await conn.execute("""
            INSERT INTO analyses 
            (analysis_id, session_id, topic, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            analysis_id,
            session_id,
            topic,
            content,
            datetime.now()
        ))
        
        await conn.commit()

    async def get_analysis(self, analysis_id: str) -> Optional[AnalysisResponse]:
        """분석 결과 조회"""
        conn = await db_manager.get_connection()
        
        async with conn.execute("""
            SELECT analysis_id, session_id, topic, content, created_at
            FROM analyses 
            WHERE analysis_id = ?
        """, (analysis_id,)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return None
                
            return AnalysisResponse(
                analysis_id=row[0],
                session_id=row[1],
                topic=row[2],
                content=row[3],
                created_at=datetime.fromisoformat(row[4])
            )

    async def _save_presentation_with_analysis(
        self, 
        presentation_id: str,
        analysis_id: str,
        session_id: str,
        title: str,
        topic: str,
        content: str,
        marp_content: str,
        theme: str
    ):
        """분석 기반 발표자료를 데이터베이스에 저장"""
        conn = await db_manager.get_connection()
        
        await conn.execute("""
            INSERT INTO presentations 
            (presentation_id, analysis_id, session_id, title, topic, content, marp_content, theme, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            presentation_id,
            analysis_id,
            session_id,
            title,
            topic,
            content,
            marp_content,
            theme,
            datetime.now(),
            datetime.now()
        ))
        
        await conn.commit()


# 전역 발표자료 서비스 인스턴스
presentation_service = PresentationService()