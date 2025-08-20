# 챗봇 백엔드 서버 구현 계획

## 📋 전체 구현 계획 (서브태스크 단위)

### Phase 1: 프로젝트 기반 구조 설정
- [x] **데이터베이스 모델 설계**: SQLite 기반 sessions/messages 테이블 구조 정의
- [x] **FastAPI 프로젝트 구조 생성**: 디렉토리 구조 및 기본 파일들 생성  
- [x] **환경 설정**: requirements.txt, config.py, .env 파일 생성

### Phase 2: 코어 서비스 구현
- [x] **데이터베이스 연결**: SQLite 연결 및 테이블 생성 로직 구현
- [x] **LLM 클라이언트**: midm_LLM_serving 서버와 통신하는 클라이언트 구현
- [x] **세션 서비스**: 세션 생성/조회/삭제 로직 구현
- [x] **채팅 서비스**: 메시지 저장 및 컨텍스트 관리 로직 구현

### Phase 3: API 엔드포인트 구현
- [x] **세션 API**: POST /api/sessions, GET /api/sessions/{id}, DELETE /api/sessions/{id}
- [x] **채팅 API**: POST /api/chat (일반 응답)
- [x] **스트리밍 API**: POST /api/chat/stream (SSE 기반)
- [x] **히스토리 API**: GET /api/sessions/{id}/messages
- [x] **헬스체크 API**: GET /api/health

### Phase 4: 통합 및 테스트
- [x] **메인 앱 구성**: FastAPI 앱 엔트리포인트 및 라우터 등록
- [ ] **통합 테스트**: LLM 서버와의 연동 테스트
- [ ] **문서화 완료**: 전체 계획 및 구현 완료 상태 업데이트

## 🏗️ 구현할 디렉토리 구조
```
Chatbot_Backend/
├── tasks.md                # 이번에 생성할 계획 문서
├── main.py                 # FastAPI 앱 엔트리포인트  
├── config.py               # 환경설정
├── requirements.txt        # 의존성 관리
├── models/
│   ├── __init__.py
│   ├── database.py        # SQLite 연결 및 테이블
│   └── schemas.py         # Pydantic 모델
├── services/
│   ├── __init__.py
│   ├── session_service.py # 세션 관리
│   ├── chat_service.py    # 채팅 로직
│   └── llm_client.py      # LLM 서버 통신
└── api/
    ├── __init__.py
    ├── sessions.py        # 세션 라우터
    ├── chat.py           # 채팅 라우터
    └── health.py         # 헬스체크
```

## 🔌 LLM 서버 연동 방식
- midm_LLM_serving의 `/chat` (일반) 및 `/chat/stream` (스트리밍) 엔드포인트 활용
- 기존 Message/ChatRequest 모델 구조 재사용
- SSE 스트림을 백엔드에서 프록시하여 클라이언트에 전달

## 📊 데이터베이스 스키마
```sql
-- sessions 테이블
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON 형태로 저장
);

-- messages 테이블  
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT,
    role TEXT CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_usage TEXT,  -- JSON 형태로 저장
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);
```

## 🔧 주요 API 스펙
### 세션 생성
- **POST** `/api/sessions`
- Response: `{"session_id": "uuid", "created_at": "timestamp"}`

### 채팅 요청
- **POST** `/api/chat`
- Request: `{"session_id": "uuid", "message": "text"}`
- Response: `{"message_id": "uuid", "role": "assistant", "content": "text", "created_at": "timestamp"}`

### 스트리밍 채팅
- **POST** `/api/chat/stream`
- Request: `{"session_id": "uuid", "message": "text"}`
- Response: SSE 스트림

### 히스토리 조회
- **GET** `/api/sessions/{id}/messages`
- Response: `{"messages": [...]}`