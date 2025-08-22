import re
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
                "analysis": analysis.model_dump(mode='json') if analysis else None
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
                "presentation": presentation.model_dump(mode='json') if presentation else None
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "message": f"발표자료 변환 중 오류가 발생했습니다: {str(e)}"
            }




    async def _convert_to_marp_stream(self, content: str) -> AsyncGenerator[Dict, None]:
        """상세 내용을 Marp 형식으로 변환 (직접 변환)"""
        # 직접 Marp 변환 로직 실행
        marp_content = self._convert_to_marp_direct(content)
        
        # 변환된 내용을 청크 단위로 전송
        chunk_size = 100  # 적당한 청크 크기
        for i in range(0, len(marp_content), chunk_size):
            chunk = marp_content[i:i+chunk_size]
            yield {
                "type": "chunk",
                "content": chunk
            }
        
        # 완료 신호
        yield {
            "type": "complete"
        }

    def _convert_to_marp_direct(self, content: str) -> str:
        """분석 내용을 직접 Marp 형식으로 변환"""
        
        lines = content.split('\n')
        
        # Marp 헤더
        marp_content = [
            "---",
            "marp: true",
            "theme: default",
            "paginate: true",
            "backgroundColor: #fff",
            "---",
            ""
        ]
        
        # 제목 추출 (첫 번째 섹션이나 주제에서)
        title = self._extract_title(content)
        
        # 타이틀 슬라이드
        marp_content.extend([
            f"# {title} <!-- fit -->",
            "",
            "## 발표자료",
            f"**생성일: {datetime.now().strftime('%Y-%m-%d')}**",
            "",
            "---",
            ""
        ])
        
        # 섹션 파싱 및 슬라이드 생성
        sections = self._parse_sections(content)
        
        # 목차 슬라이드
        if len(sections) > 1:
            marp_content.extend([
                "## 목차",
                ""
            ])
            for i, section in enumerate(sections, 1):
                marp_content.append(f"{i}. **{section['title']}**")
            marp_content.extend(["", "---", ""])
        
        # 각 섹션을 슬라이드로 변환
        for section in sections:
            slides = self._section_to_slides(section)
            marp_content.extend(slides)
        
        return '\n'.join(marp_content)

    def _extract_title(self, content: str) -> str:
        """내용에서 제목 추출"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('*'):
                # 마크다운 헤더 제거
                title = re.sub(r'^#+\s*', '', line)
                # 볼드 마크다운 제거
                title = re.sub(r'\*\*(.*?)\*\*', r'\1', title)
                if len(title) > 5:  # 너무 짧은 제목 제외
                    return title[:50]  # 제목 길이 제한
        return "발표자료"

    def _parse_sections(self, content: str) -> list:
        """내용을 섹션별로 파싱"""
        
        sections = []
        current_section = None
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 섹션 제목 감지 (**, ##, ###, 1., 2. 등)
            section_match = re.match(r'^(\*\*([^*]+)\*\*|#{1,3}\s*([^#]+)|(\d+)\.\s*\*\*([^*]+)\*\*)', line)
            
            if section_match:
                # 이전 섹션 저장
                if current_section and current_section['content']:
                    sections.append(current_section)
                
                # 새 섹션 시작
                title = section_match.group(2) or section_match.group(3) or section_match.group(5)
                if title:
                    title = title.strip()
                    current_section = {
                        'title': title,
                        'content': []
                    }
            else:
                # 현재 섹션에 내용 추가
                if current_section is not None:
                    current_section['content'].append(line)
        
        # 마지막 섹션 저장
        if current_section and current_section['content']:
            sections.append(current_section)
        
        return sections

    def _section_to_slides(self, section: dict) -> list:
        """섹션을 슬라이드로 변환"""
        slides = []
        title = section['title']
        content_lines = section['content']
        
        # 내용을 슬라이드 단위로 분할 (최대 4-5줄)
        max_lines_per_slide = 4
        
        if len(content_lines) <= max_lines_per_slide:
            # 한 슬라이드로 충분
            slides.extend([
                f"## {title}",
                ""
            ])
            for line in content_lines:
                formatted_line = self._format_line(line)
                if formatted_line:
                    slides.append(formatted_line)
            slides.extend(["", "---", ""])
        else:
            # 여러 슬라이드로 분할
            chunks = [content_lines[i:i+max_lines_per_slide] 
                     for i in range(0, len(content_lines), max_lines_per_slide)]
            
            for i, chunk in enumerate(chunks, 1):
                if len(chunks) > 1:
                    slides.append(f"## {title} ({i}/{len(chunks)})")
                else:
                    slides.append(f"## {title}")
                slides.append("")
                
                for line in chunk:
                    formatted_line = self._format_line(line)
                    if formatted_line:
                        slides.append(formatted_line)
                slides.extend(["", "---", ""])
        
        return slides

    def _format_line(self, line: str) -> str:
        """라인을 Marp 형식으로 포맷팅"""
        
        line = line.strip()
        if not line:
            return ""
        
        # 이미 불릿 포인트면 그대로
        if line.startswith('- ') or line.startswith('* '):
            return line
        
        # 번호 목록을 불릿 포인트로 변환
        if re.match(r'^\d+\.\s', line):
            pattern = r'^\d+\.\s*'
            return f"- {re.sub(pattern, '', line)}"
        
        # 일반 텍스트를 불릿 포인트로 변환
        if len(line) > 10:  # 너무 짧은 내용 제외
            return f"- {line}"
        
        return line


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