from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key")
    )
    JINA_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("JINA_API_KEY", "jina_api_key")
    )

    KRISHA_APP_ID: str = Field(
        ..., validation_alias=AliasChoices("KRISHA_APP_ID", "krisha_app_id")
    )
    KRISHA_APP_KEY: str = Field(
        ..., validation_alias=AliasChoices("KRISHA_APP_KEY", "krisha_app_key")
    )
    BASE_URL: str = Field(..., validation_alias=AliasChoices("BASE_URL", "base_url"))

    LOG_LEVEL: str = Field(
        default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "log_level")
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()  # type: ignore[call-arg]
