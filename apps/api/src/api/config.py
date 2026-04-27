from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    storage_dir: Path = Path("./storage")
    demucs_model: str = "htdemucs"
    transcriber: Literal["basic_pitch", "crepe"] = "basic_pitch"
    bass_tuning: Literal["4string", "5string"] = "5string"
    redis_url: str = "redis://localhost:6379"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
