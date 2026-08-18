"""
app/core/config.py

One object, one import, every setting.
Never call os.getenv() anywhere else. Import settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # --- Groq ---
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.2
    STT_MODEL: str = "whisper-large-v3-turbo"

    # --- Pexels (car images) ---
    PEXELS_API_KEY: str = ""

    # --- Storage ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/pakwheels_db"
    CATALOG_PATH: str = "catalog.json"

    # --- App ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    MAX_CONDITION_QUESTIONS: int = 2

    class Config:
        env_file = ".env"


settings = Settings()