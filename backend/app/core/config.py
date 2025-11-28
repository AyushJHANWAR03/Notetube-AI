from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # OpenAI
    OPENAI_API_KEY: str

    # Firebase (for PDF storage)
    FIREBASE_PROJECT_ID: str | None = None
    FIREBASE_STORAGE_BUCKET: str | None = None
    FIREBASE_CREDENTIALS_PATH: str | None = None

    # App
    FRONTEND_URL: str
    BACKEND_URL: str
    ENVIRONMENT: str = "development"

    # YouTube (optional)
    YOUTUBE_COOKIES_FILE: str | None = None
    PROXY_URL: str | None = None
    PROXY_LIST: str | None = None

    # Supadata.ai (for YouTube transcripts - primary provider)
    SUPADATA_API_KEY: str | None = None

    # API
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "NoteTube AI"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
