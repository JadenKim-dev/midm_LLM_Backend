import aiosqlite

DATABASE_PATH = "chatbot.db"

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._connection = None
    
    async def connect(self):
        """데이터베이스 연결"""
        self._connection = await aiosqlite.connect(self.db_path)
        await self.create_tables()
    
    async def disconnect(self):
        """데이터베이스 연결 해제"""
        if self._connection:
            await self._connection.close()
    
    async def create_tables(self):
        """테이블 생성"""
        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            );
            
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                token_usage TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        """)
        await self._connection.commit()
    
    async def get_connection(self):
        """데이터베이스 연결 반환"""
        if not self._connection:
            await self.connect()
        return self._connection

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()