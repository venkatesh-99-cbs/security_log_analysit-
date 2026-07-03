from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Security Log Analysis Assistant"
    API_V1_STR: str = "/api/v1"

    # Database
    SQLITE_URL: str = "sqlite:///./security_assistant.db"
    CHROMA_DB_PATH: str = "./chroma_db"

    # AI - Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3.5:9b"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    REPORT_DIR: str = "./reports"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        case_sensitive = True

settings = Settings()
