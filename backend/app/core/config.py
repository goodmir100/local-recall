import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "LocalRecall"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOCAL_RECALL_", env_file=".env", extra="ignore")

    data_dir: Path = APP_DIR
    capture_interval_seconds: int = 5
    dedupe_threshold: int = 5
    retention_days: int = 30
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "recall.db"


settings = Settings()
os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.screenshots_dir, exist_ok=True)
