"""Pydantic Settings configuration for the Library Management System."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # ── App ──
    PROJECT_NAME: str = "Library Management System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://admin:admin@localhost:5433/library_db"

    # ── Auth / JWT ──
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── Library Config ──
    BORROW_PERIOD_DAYS: int = 14
    MAX_BOOKS_PER_MEMBER: int = 5

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


settings = Settings()
