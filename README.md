# 챗봇 백엔드 API

LLM 서버와 통신하는 챗봇 백엔드 서버입니다. 세션 관리, 대화 히스토리 저장, 실시간 스트리밍 채팅을 지원합니다.

## 🚀 빠른 시작

### 1. 사전 요구사항

- Python 3.8 이상
- LLM 서버 (`midm_LLM_serving`) 실행 중

### 2. 설치 및 실행

```bash
# 1. 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 서버 실행
python main.py
```

서버가 성공적으로 시작되면 http://localhost:8080 에서 접근 가능합니다.

## 📖 API 문서

### 자동 생성 문서
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### 주요 엔드포인트

#### 🔐 세션 관리
```http
# 새 세션 생성
POST /api/sessions
Content-Type: application/json

{
  "metadata": {"user_id": "example"}  # 선택사항
}

# 세션 정보 조회
GET /api/sessions/{session_id}

# 세션 삭제 (메시지 포함)
DELETE /api/sessions/{session_id}

# 세션의 메시지 히스토리 조회
GET /api/sessions/{session_id}/messages?limit=10
```

#### 💬 채팅
```http
# 일반 채팅 (완성된 응답)
POST /api/chat
Content-Type: application/json

{
  "session_id": "uuid-here",
  "message": "안녕하세요!",
  "max_new_tokens": 256,
  "temperature": 0.7,
  "do_sample": true
}

# 스트리밍 채팅 (실시간 응답)
POST /api/chat/stream
Content-Type: application/json
# 동일한 요청 본문, SSE 형태로 응답
```

#### 🏥 헬스체크
```http
# 서버 및 의존성 상태 확인
GET /api/health
```

## 🛠️ 환경 설정

환경변수를 통해 서버 설정을 변경할 수 있습니다:

```bash
# .env 파일 생성 또는 환경변수 설정
export LLM_SERVER_URL=http://localhost:8000        # LLM 서버 주소
export DATABASE_URL=chatbot.db                     # SQLite 데이터베이스 파일
export MAX_CONTEXT_MESSAGES=10                     # 컨텍스트로 사용할 최대 메시지 수
export DEFAULT_MAX_TOKENS=256                      # 기본 최대 토큰 수
export DEFAULT_TEMPERATURE=0.7                     # 기본 생성 온도
export SESSION_TIMEOUT_HOURS=24                    # 세션 만료 시간(시간)
export HOST=0.0.0.0                               # 서버 호스트
export PORT=8080                                  # 서버 포트
export DEBUG=false                                # 디버그 모드
export CORS_ORIGINS="*"                           # CORS 허용 도메인 (콤마 구분)
```

## 📂 프로젝트 구조

```
Chatbot_Backend/
├── main.py                 # FastAPI 앱 엔트리포인트
├── config.py               # 환경설정 관리
├── requirements.txt        # Python 의존성
├── README.md              # 이 파일
├── tasks.md               # 개발 계획 및 진행상황
├── models/
│   ├── __init__.py
│   ├── database.py        # SQLite 연결 및 테이블 관리
│   └── schemas.py         # Pydantic 데이터 모델
├── services/
│   ├── __init__.py
│   ├── session_service.py # 세션 관리 로직
│   ├── chat_service.py    # 채팅 처리 로직
│   └── llm_client.py      # LLM 서버 통신 클라이언트
└── api/
    ├── __init__.py
    ├── sessions.py        # 세션 관련 API 라우터
    ├── chat.py           # 채팅 관련 API 라우터
    └── health.py         # 헬스체크 API 라우터
```

## 🔧 실행 옵션

### 개발 모드
```bash
# 자동 재로드 활성화
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 운영 모드
```bash
# Gunicorn 사용 (Linux/macOS)
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
```

## 🗄️ 데이터베이스

SQLite를 사용하여 다음 테이블을 자동 생성합니다:

- **sessions**: 세션 정보 (session_id, created_at, last_accessed, metadata)
- **messages**: 메시지 히스토리 (message_id, session_id, role, content, created_at, token_usage)

데이터베이스 파일은 `chatbot.db`로 생성되며, 서버 재시작 시에도 데이터가 유지됩니다.

## 📝 사용 예시

### Python 클라이언트 예시
```python
import httpx
import json

# 1. 세션 생성
async with httpx.AsyncClient() as client:
    session_response = await client.post("http://localhost:8080/api/sessions")
    session_id = session_response.json()["session_id"]
    
    # 2. 채팅 요청
    chat_response = await client.post("http://localhost:8080/api/chat", json={
        "session_id": session_id,
        "message": "안녕하세요!"
    })
    print(chat_response.json()["content"])
```

### curl 예시
```bash
# 세션 생성
SESSION_ID=$(curl -X POST http://localhost:8080/api/sessions | jq -r .session_id)

# 채팅 요청
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"message\": \"안녕하세요!\"
  }"
```

## 🚨 문제 해결

### 일반적인 오류

**1. LLM 서버 연결 실패**
```
HTTPException: LLM server not available
```
- LLM 서버가 실행 중인지 확인
- `LLM_SERVER_URL` 환경변수 확인

**2. 세션 없음 오류**
```
HTTPException: Session {id} not found
```
- 유효한 세션 ID를 사용하는지 확인
- 세션이 만료되었을 가능성 (기본 24시간)

**3. 데이터베이스 오류**
```
Database connection failed
```
- 파일 쓰기 권한 확인
- 디스크 용량 확인

### 로그 확인
```bash
# 실행 시 로그 레벨 설정
uvicorn main:app --log-level debug
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
