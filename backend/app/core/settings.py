import os
import json
from pydantic_settings import BaseSettings
from typing import List

# Path for user settings persistence
USER_SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "user_settings.json"
)

def get_user_settings_model() -> str:
    try:
        if os.path.exists(USER_SETTINGS_PATH):
            with open(USER_SETTINGS_PATH, "r") as f:
                return json.load(f).get("ollama_model", "")
    except Exception:
        pass
    return ""


class Settings(BaseSettings):
    PROJECT_NAME: str = "Security Log Analysis Assistant"
    API_V1_STR: str = "/api/v1"

    # Database
    SQLITE_URL: str = "sqlite:///./security_assistant.db"
    CHROMA_DB_PATH: str = "./chroma_db"

    # AI - Ollama
    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://127.0.0.1:11434"
    )
    OLLAMA_MODEL: str = get_user_settings_model() or os.getenv("OLLAMA_MODEL", "")
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    RECOMMENDED_OLLAMA_MODEL: str = "qwen2.5:3b-instruct"
    OLLAMA_MODEL_FALLBACKS: List[str] = [
        "qwen3.5:9b",
        "qwen2.5:7b",
        "qwen2.5:3b-instruct",
        "llama3.2:3b",
        "phi3:mini",
        "mistral:7b",
        "qwen2.5:1.5b-instruct",
    ]

    # AI - Ollama context / model-selection tuning
    # Ceiling on num_ctx (tokens). Raise this if you have RAM/VRAM to spare and
    # want even longer reports; lower it on constrained machines to avoid OOM.
    OLLAMA_MAX_CONTEXT: int = int(os.getenv("OLLAMA_MAX_CONTEXT", "16384"))
    # Floor on num_ctx (tokens), used even for short prompts so replies never
    # start cramped.
    OLLAMA_MIN_CONTEXT: int = int(os.getenv("OLLAMA_MIN_CONTEXT", "4096"))
    # When True (default), the client scores every installed model by real
    # context length + parameter size and auto-picks the best fit for each
    # request, unless OLLAMA_MODEL above is explicitly set to an installed
    # model (which always wins as a manual pin). Set False to always use
    # OLLAMA_MODEL / the OLLAMA_MODEL_FALLBACKS candidate list instead.
    OLLAMA_AUTO_SELECT_MODEL: bool = os.getenv("OLLAMA_AUTO_SELECT_MODEL", "true").lower() in ("1", "true", "yes")

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    REPORT_DIR: str = "./reports"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        case_sensitive = True

settings = Settings()