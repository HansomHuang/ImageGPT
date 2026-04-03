from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tomllib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "backend" / "config.default.toml"


def _toml_defaults() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


_DEFAULTS = _toml_defaults()
_OPENAI = _DEFAULTS.get("openai", {})
_BACKEND = _DEFAULTS.get("backend", {})
_EXPORT = _DEFAULTS.get("export", {})
_STORAGE = _DEFAULTS.get("storage", {})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default=_OPENAI.get("model", "gpt-4.1-mini"), alias="OPENAI_MODEL")

    backend_host: str = Field(default=_BACKEND.get("host", "127.0.0.1"), alias="IMGGPT_BACKEND_HOST")
    backend_port: int = Field(default=_BACKEND.get("port", 8000), alias="IMGGPT_BACKEND_PORT")
    log_level: str = Field(default=_BACKEND.get("log_level", "INFO"), alias="IMGGPT_LOG_LEVEL")
    preview_max_edge: int = Field(default=_BACKEND.get("preview_max_edge", 1536), alias="IMGGPT_PREVIEW_MAX_EDGE")
    jpeg_quality: int = Field(default=_EXPORT.get("jpeg_quality", 92), alias="IMGGPT_JPEG_QUALITY")
    enable_telemetry: bool = Field(default=False, alias="IMGGPT_ENABLE_TELEMETRY")

    db_path: Path = Field(
        default=ROOT_DIR / _STORAGE.get("db_path", "backend/data/imagegpt.db"),
        alias="IMGGPT_DB_PATH",
    )
    recipes_dir: Path = Field(
        default=ROOT_DIR / _STORAGE.get("recipes_dir", "backend/data/recipes"),
        alias="IMGGPT_RECIPES_DIR",
    )
    presets_dir: Path = Field(
        default=ROOT_DIR / _STORAGE.get("presets_dir", "backend/data/presets"),
        alias="IMGGPT_PRESETS_DIR",
    )
    export_dir: Path = Field(
        default=ROOT_DIR / _STORAGE.get("exports_dir", "backend/data/exports"),
        alias="IMGGPT_EXPORT_DIR",
    )

    schema_path: Path = ROOT_DIR / "schemas" / "recipe.schema.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.recipes_dir.mkdir(parents=True, exist_ok=True)
    settings.presets_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
