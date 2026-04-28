"""
Configuration management for Swaya.me
Loads and validates environment variables using Pydantic Settings
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=3306, alias="DB_PORT")
    name: str = Field(default="swaya_dev", alias="DB_NAME")
    user: str = Field(default="root", alias="DB_USER")
    password: str = Field(default="", alias="DB_PASSWORD")
    pool_size: int = Field(default=50, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=100, alias="DB_MAX_OVERFLOW")
    pool_recycle: int = Field(default=3600, alias="DB_POOL_RECYCLE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def url(self) -> str:
        """Generate database URL (sync)"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_url(self) -> str:
        """Generate async database URL"""
        return f"mysql+asyncmy://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: str = Field(default="", alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB")
    pool_size: int = Field(default=50, alias="REDIS_POOL_SIZE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def url(self) -> str:
        """Generate Redis URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class JWTSettings(BaseSettings):
    """JWT authentication configuration"""
    secret: str = Field(alias="JWT_SECRET")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class AppSettings(BaseSettings):
    """Application configuration"""
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    reload: bool = Field(default=False, alias="RELOAD")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="production", alias="ENVIRONMENT")
    login_rate_limit: str = Field(default="10/minute", alias="LOGIN_RATE_LIMIT")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    uploads_base_dir: str = Field(default="/home/vinay/Swaya.me/backend/uploads", alias="UPLOADS_BASE_DIR")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000"], 
        alias="ALLOWED_ORIGINS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class GoogleSettings(BaseSettings):
    """Google OAuth configuration"""
    client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class SMTPSettings(BaseSettings):
    """Email SMTP configuration"""
    host: str = Field(default="smtp.titan.email", alias="SMTP_HOST")
    port: int = Field(default=465, alias="SMTP_PORT")
    user: str = Field(default="", alias="SMTP_USER")
    password: str = Field(default="", alias="SMTP_PASSWORD")
    from_email: str = Field(default="info@chakrix.com", alias="SMTP_FROM_EMAIL")
    from_name: str = Field(default="Swayame", alias="SMTP_FROM_NAME")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class OllamaSettings(BaseSettings):
    """Ollama AI service configuration"""
    base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    model: str = Field(default="qwen2.5:3b", alias="OLLAMA_MODEL")
    fallback_model: str = Field(default="llama3.2:1b", alias="OLLAMA_FALLBACK_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class Settings(BaseSettings):
    """Main settings container"""
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
