import os
from functools import lru_cache

from pydantic import BaseModel
from dotenv import load_dotenv

# Load env variables if .env exists (non-fatal if not found)
load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str

    # App
    app_name: str = "Recipe Hub Backend"
    environment: str = os.getenv("REACT_APP_NODE_ENV", "development")

    # Auth / Security
    secret_key: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "recipe-hub")
    jwt_audience: str | None = os.getenv("JWT_AUDIENCE")

    # CORS
    frontend_origin: str | None = os.getenv("FRONTEND_ORIGIN")

    # Media
    media_dir: str = os.getenv(
        "MEDIA_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media")),
    )
    media_url_prefix: str = os.getenv("MEDIA_URL_PREFIX", "/media")

    @staticmethod
    def _default_database_url() -> str:
        """
        Build a default SQLite URL if DATABASE_URL is not present.
        Uses a local file sqlite database.
        """
        default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db"))
        return f"sqlite:///{default_path}"

    @classmethod
    def load(cls) -> "Settings":
        # Preferred: DATABASE_URL for PostgreSQL or other DBs
        db_url = os.getenv("DATABASE_URL")

        # If DATABASE_URL missing, fallback to SQLite file-based DB
        if not db_url or db_url.strip() == "":
            db_url = cls._default_database_url()

        # Ensure proper driver prefix adjustment if someone uses postgres://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        return cls(database_url=db_url)


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance loaded from environment variables."""
    return Settings.load()
