import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    LLM_SERVER_URL: str = os.getenv("LLM_SERVER_URL", "http://localhost:8000")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "chatbot.db")
    MAX_CONTEXT_MESSAGES: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))
    DEFAULT_MAX_TOKENS: int = int(os.getenv("DEFAULT_MAX_TOKENS", "256"))
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "500"))
    DEFAULT_CHUNK_OVERLAP: int = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "50"))
    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "3"))
    MIN_SIMILARITY_SCORE: float = float(os.getenv("MIN_SIMILARITY_SCORE", "0.7"))

settings = Settings()