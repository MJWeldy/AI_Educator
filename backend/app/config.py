from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SEED_DIR = BACKEND_DIR / "app" / "content" / "seed"


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{DATA_DIR / 'educator.db'}"
    uploads_dir: Path = DATA_DIR / "uploads"
    extracted_dir: Path = DATA_DIR / "extracted"
    ollama_base_url: str = "http://localhost:11434"
    frontend_dist: Path = PROJECT_DIR / "frontend" / "dist"

    model_config = {"env_prefix": "EDUCATOR_"}


settings = Settings()
