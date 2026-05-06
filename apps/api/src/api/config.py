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
    max_duration_sec: int = 600  # 10분. 더 길면 ML 처리에 너무 오래 걸림


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
