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
        """테이블 생성 및 마이그레이션"""
        # 기본 테이블들 생성
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
            
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                session_id TEXT,
                title TEXT,
                content TEXT,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT,
                chunk_index INTEGER,
                content TEXT,
                embedding_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id TEXT PRIMARY KEY,
                session_id TEXT,
                topic TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
            CREATE INDEX IF NOT EXISTS idx_documents_session_id ON documents(session_id);
            CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_id ON document_chunks(embedding_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_session_id ON analyses(session_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);
        """)
        
        # presentations 테이블 마이그레이션 처리
        await self._migrate_presentations_table()
        
        await self._connection.commit()
    
    async def _migrate_presentations_table(self):
        """presentations 테이블 마이그레이션"""
        # 기존 presentations 테이블 구조 확인
        cursor = await self._connection.execute("PRAGMA table_info(presentations)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'analysis_id' not in column_names:
            # 기존 테이블이 있지만 analysis_id 컬럼이 없는 경우
            print("Migrating presentations table to add analysis_id column...")
            
            # 1. 기존 데이터 백업
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS presentations_old AS 
                SELECT * FROM presentations
            """)
            
            # 2. 기존 테이블 삭제
            await self._connection.execute("DROP TABLE IF EXISTS presentations")
            
            # 3. 새로운 구조로 테이블 재생성
            await self._connection.execute("""
                CREATE TABLE presentations (
                    presentation_id TEXT PRIMARY KEY,
                    analysis_id TEXT,
                    session_id TEXT,
                    title TEXT,
                    topic TEXT,
                    content TEXT,
                    marp_content TEXT,
                    theme TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
                    FOREIGN KEY (analysis_id) REFERENCES analyses (analysis_id) ON DELETE CASCADE
                )
            """)
            
            # 4. 기존 데이터 복원 (analysis_id는 NULL로)
            try:
                await self._connection.execute("""
                    INSERT INTO presentations 
                    (presentation_id, analysis_id, session_id, title, topic, content, marp_content, theme, created_at, updated_at)
                    SELECT presentation_id, NULL, session_id, title, topic, content, marp_content, theme, created_at, updated_at
                    FROM presentations_old
                """)
                print("Successfully migrated existing presentation data")
            except Exception as e:
                print(f"Warning: Could not migrate existing data: {e}")
            
            # 5. 백업 테이블 삭제
            await self._connection.execute("DROP TABLE IF EXISTS presentations_old")
            
        else:
            # analysis_id 컬럼이 이미 있는 경우, 테이블이 없으면 생성만
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS presentations (
                    presentation_id TEXT PRIMARY KEY,
                    analysis_id TEXT,
                    session_id TEXT,
                    title TEXT,
                    topic TEXT,
                    content TEXT,
                    marp_content TEXT,
                    theme TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,
                    FOREIGN KEY (analysis_id) REFERENCES analyses (analysis_id) ON DELETE CASCADE
                )
            """)
        
        # 인덱스 생성
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_presentations_session_id ON presentations(session_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_presentations_analysis_id ON presentations(analysis_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_presentations_created_at ON presentations(created_at)")
    
    async def get_connection(self):
        """데이터베이스 연결 반환"""
        if not self._connection:
            await self.connect()
        return self._connection

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()