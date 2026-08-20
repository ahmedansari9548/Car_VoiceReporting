"""
app/core/config.py

One object, one import, every setting.
Never call os.getenv() anywhere else. Import settings.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

# Load environment variables from backend/.env or root/.env if present
for env_path in (BASE_DIR / ".env", ROOT_DIR / ".env", Path(".env")):
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


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
    # Every origin the browser may load the frontend from. A missing entry
    # here shows up in the browser console as a CORS error on /api/cars while
    # the WebSocket (which CORS does not govern) still works — a confusing
    # half-broken state. Override with CORS_ORIGINS in .env if you add a domain.
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://59.103.233.98:7072",
    ]
    MAX_CONDITION_QUESTIONS: int = 2

    model_config = SettingsConfigDict(
        env_file=(
            BASE_DIR / ".env",
            ROOT_DIR / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("CATALOG_PATH", mode="after")
    @classmethod
    def resolve_catalog_path(cls, v: str) -> str:
        p = Path(v)
        if not p.is_absolute():
            candidate = BASE_DIR / p
            if candidate.exists():
                return str(candidate)
        return v


settings = Settings()