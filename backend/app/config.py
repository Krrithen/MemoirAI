from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings have local defaults, so the app runs with no .env at all.

    Hosted providers are opt-in: set TRANSCRIBER=assemblyai or LLM=gemini
    and the matching API key.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://memoir:memoir@localhost:5433/memoir"
    media_dir: str = "data/media"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    max_audio_bytes: int = 100 * 1024 * 1024
    max_video_bytes: int = 50 * 1024 * 1024
    max_image_bytes: int = 5 * 1024 * 1024

    transcriber: Literal["whisper", "assemblyai"] = "whisper"
    whisper_model: str = "small"
    whisper_compute_type: str = "int8"

    llm: Literal["ollama", "gemini"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    llm_timeout_s: float = 120.0
    # creative: vivid retelling that may add atmosphere; faithful: light edit that adds nothing
    story_style: Literal["creative", "faithful"] = "creative"
    llm_temperature: float | None = None  # None = the story style's default

    assemblyai_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
