"""Application configuration models."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Primary application settings."""

    openai_api_key: SecretStr = Field(
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            "DIGEST_OPENAI_API_KEY",
            "DIGEST_DASHSCOPE_API_KEY",
            "DASHSCOPE_API_KEY",
        ),
    )
    openai_model: str = Field(
        default="qwen3-max",
        validation_alias=AliasChoices(
            "OPENAI_MODEL",
            "LLM_MODEL",
        ),
    )
    openai_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias=AliasChoices(
            "OPENAI_BASE_URL",
            "DIGEST_OPENAI_BASE_URL",
            "DIGEST_DASHSCOPE_BASE_URL",
            "DASHSCOPE_BASE_URL",
        ),
    )
    summarizer_temperature: float = Field(
        default=0.2,
        validation_alias=AliasChoices(
            "SUMMARIZER_TEMPERATURE",
            "DIGEST_SUMMARIZER_TEMPERATURE",
        ),
    )
    summarizer_max_tokens: int = Field(
        default=180,
        validation_alias=AliasChoices(
            "SUMMARIZER_MAX_TOKENS",
            "DIGEST_SUMMARIZER_MAX_TOKENS",
        ),
    )

    gmail_credentials_path: Path = Field(
        default=Path("credentials.json"),
        validation_alias=AliasChoices(
            "GMAIL_CREDENTIALS_PATH",
            "DIGEST_GMAIL_CREDENTIALS_PATH",
        ),
    )
    gmail_token_path: Path = Field(
        default=Path("token.json"),
        validation_alias=AliasChoices(
            "GMAIL_TOKEN_PATH",
            "DIGEST_GMAIL_TOKEN_PATH",
        ),
    )

    output_dir: Path = Field(
        default=Path("artifacts/digests"),
        validation_alias=AliasChoices(
            "OUTPUT_DIR",
            "DIGEST_OUTPUT_DIR",
        ),
    )
    summary_csv_path: Path = Field(
        default=Path("artifacts/summary.csv"),
        validation_alias=AliasChoices(
            "SUMMARY_CSV_PATH",
            "DIGEST_SUMMARY_CSV_PATH",
        ),
    )

    default_unread: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "DEFAULT_UNREAD",
            "DIGEST_DEFAULT_UNREAD",
        ),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices(
            "LOG_LEVEL",
            "DIGEST_LOG_LEVEL",
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
    )


_SETTINGS: AppSettings | None = None


def get_settings() -> AppSettings:
    """Load application settings from the environment."""
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = AppSettings()  # type: ignore[call-arg]
    return _SETTINGS
