LLM 서버와 통신하는 챗봇 백엔드 서버 설계입니다. MVP 형태로 최소한의 채팅 기능만 구현하는 방향의 계획입니다.

## 📋 챗봇 백엔드 서버 설계 계획

### 1. **핵심 기능 정의**
- 사용자 세션 관리 (간단한 세션 ID 기반)
- 대화 히스토리 저장 및 조회
- LLM 서버와의 통신 (일반 응답 및 스트리밍)
- 대화 컨텍스트 관리

### 2. **데이터 모델 설계**

```python
# SQLite 테이블 구조
"""
sessions 테이블:
- session_id (PRIMARY KEY): UUID
- created_at: TIMESTAMP
- last_accessed: TIMESTAMP
- metadata: JSON (선택적 사용자 정보 등)

messages 테이블:
- message_id (PRIMARY KEY): UUID
- session_id (FOREIGN KEY): UUID
- role: TEXT ('user' | 'assistant' | 'system')
- content: TEXT
- created_at: TIMESTAMP
- token_usage: JSON (optional)
"""
```

### 3. **API 엔드포인트 설계**

```python
# 1. 세션 관리
POST   /api/sessions           # 새 세션 생성
GET    /api/sessions/{id}      # 세션 정보 조회
DELETE /api/sessions/{id}      # 세션 삭제 (대화 기록 포함)

# 2. 채팅 기능
POST   /api/chat               # 일반 채팅 (완성된 응답)
POST   /api/chat/stream        # 스트리밍 채팅 (SSE)
GET    /api/sessions/{id}/messages  # 대화 히스토리 조회

# 3. 헬스체크
GET    /api/health             # 서버 상태 확인
```

### 4. **주요 컴포넌트 구조**

```
chatbot-backend/
├── main.py                 # FastAPI 앱 엔트리포인트
├── config.py              # 설정 관리
├── models/
│   ├── __init__.py
│   ├── database.py        # SQLite 연결 및 테이블 정의
│   └── schemas.py         # Pydantic 모델
├── services/
│   ├── __init__.py
│   ├── session_service.py # 세션 관리 로직
│   ├── chat_service.py    # 채팅 로직
│   └── llm_client.py      # LLM 서버 통신 클라이언트
├── api/
│   ├── __init__.py
│   ├── sessions.py        # 세션 관련 라우터
│   ├── chat.py           # 채팅 관련 라우터
│   └── health.py         # 헬스체크 라우터
└── requirements.txt
```

### 5. **핵심 플로우**

#### 일반 채팅 플로우:
1. 클라이언트 → 챗봇 백엔드: 세션 ID와 메시지 전송
2. 백엔드: 세션 검증 및 대화 히스토리 조회
3. 백엔드 → LLM 서버: 컨텍스트 포함하여 요청
4. LLM 서버 → 백엔드: 응답 생성
5. 백엔드: DB에 메시지 저장
6. 백엔드 → 클라이언트: 응답 반환

#### 스트리밍 채팅 플로우:
1. 동일한 1-3 단계
2. LLM 서버 → 백엔드: SSE 스트림
3. 백엔드 → 클라이언트: SSE 프록시
4. 스트림 완료 후 DB에 전체 메시지 저장

### 6. **주요 고려사항**

**세션 관리:**
- 세션 ID는 UUID로 자동 생성
- 세션 타임아웃 설정 (예: 24시간 미활동 시 자동 삭제)
- 메모리 DB이므로 서버 재시작 시 데이터 소실 (MVP에서는 허용)

**컨텍스트 관리:**
- 최근 N개 메시지만 컨텍스트로 전송 (토큰 제한 고려)

**에러 처리:**
- LLM 서버 연결 실패 처리
- 세션 없음/만료 처리

### 7. **환경 변수 설정**

```env
# .env 파일
LLM_SERVER_URL=http://localhost:8000
MAX_CONTEXT_MESSAGES=10
SESSION_TIMEOUT_HOURS=24
DATABASE_URL=sqlite:///:memory:
```

### 8. **API 요청/응답 예시**

**세션 생성:**
```json
POST /api/sessions
Response: {
  "session_id": "uuid-xxx",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**채팅 요청:**
```json
POST /api/chat
{
  "session_id": "uuid-xxx",
  "message": "안녕하세요"
}

Response: {
  "message_id": "uuid-yyy",
  "role": "assistant",
  "content": "안녕하세요! 무엇을 도와드릴까요?",
  "created_at": "2024-01-01T00:00:00Z"
}
```
