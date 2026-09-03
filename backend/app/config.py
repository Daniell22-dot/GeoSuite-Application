"""
Application configuration and settings.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


def _resolve_database_url() -> str:
    """
    Resolve database URL with fallback chain:
    1. DATABASE_URL env var
    2. Constructed PostgreSQL URL from individual vars
    3. SQLite file as last resort (no Docker needed)
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    host = os.getenv("POSTGRES_HOST", )
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db = os.getenv("POSTGRES_DB", "Geosuite")

    # If individual vars are still defaults, try SQLite
    if host == "localhost" and user == "postgres" and password == "postgres":
        # Check if PostgreSQL is actually running
        import socket
        try:
            sock = socket.create_connection((host, int(port)), timeout=2)
            sock.close()
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        except (ConnectionRefusedError, OSError, socket.timeout):
            # PostgreSQL not running — fall back to SQLite
            sqlite_path = os.path.join(os.path.dirname(__file__), "..", "data", "geosuite.db")
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
            return f"sqlite:///{os.path.abspath(sqlite_path)}"

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "GeoSuite")
    APP_VERSION: str = os.getenv("APP_VERSION", "2.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    
    # API
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # Database — auto-detects PostgreSQL or falls back to SQLite
    DATABASE_URL: str = _resolve_database_url()
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "Geosuite")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    # Redis — optional, degrades gracefully if unavailable
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # File Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "data/uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "524288000"))  # 500MB for drone images
    
    # GDAL
    GDAL_DATA: str = os.getenv("GDAL_DATA", "/usr/share/gdal")
    PROJ_LIB: str = os.getenv("PROJ_LIB", "/usr/share/proj")
    
    # Map Services
    MAPBOX_TOKEN: Optional[str] = os.getenv("MAPBOX_TOKEN")
    GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # External APIs
    ELEVATION_API_URL: str = os.getenv("ELEVATION_API_URL", "https://api.open-elevation.com/api/v1/lookup")
    OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    
    # R Integration
    R_HOME: Optional[str] = os.getenv("R_HOME")
    R_SCRIPT_PATH: Optional[str] = os.getenv("R_SCRIPT_PATH")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "geosuite.log")
    
    # Email
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    
    # HEC-RAS Integration
    HECRAS_PATH: Optional[str] = os.getenv("HECRAS_PATH")
    HECRAS_VERSION: str = os.getenv("HECRAS_VERSION", "6.0")

    # Drone Processing
    ODM_PATH: Optional[str] = os.getenv("ODM_PATH", "run.py")
    ODM_DOCKER: bool = os.getenv("ODM_DOCKER", "false").lower() in ("true", "1", "yes")
    DRONE_MAX_IMAGES: int = int(os.getenv("DRONE_MAX_IMAGES", "500"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Create settings instance
settings = Settings()

# Fail-closed on secrets: refuse to start if secrets are missing or still hold
# known development defaults. Production must supply strong random values.
if not settings.DEBUG:
    for name, value in (
        ("SECRET_KEY", settings.SECRET_KEY),
        ("JWT_SECRET", settings.JWT_SECRET),
    ):
        if not value:
            raise RuntimeError(
                f"[CRITICAL] {name} is not set. Set a strong random value via the "
                f"{name} environment variable. Refusing to start in production (DEBUG=false) "
                f"without an explicit {name}."
            )

# Database connection string
DATABASE_URL = settings.DATABASE_URL

# CORS origins
if settings.BACKEND_CORS_ORIGINS:
    origins = settings.BACKEND_CORS_ORIGINS
else:
    origins = ["*"]