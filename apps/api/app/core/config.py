"""
Configuración central de VotoSeguro respaldada por Pydantic Settings
"""
from typing import List
from pydantic import Field, model_validator
from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Entorno
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    PROJECT_NAME: str = "VotoSeguro API"
    VERSION: str = "1.0.0"

    # Base de Datos
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://votoseguro:votoseguro_secret_2026@localhost:5432/votoseguro_db"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql+psycopg://votoseguro:votoseguro_secret_2026@localhost:5432/votoseguro_db"
    )
    PGHOST: str | None = None
    PGPORT: int = 5432
    PGUSER: str | None = None
    PGPASSWORD: str | None = None
    PGDATABASE: str = "votoseguro"
    DATABASE_SSL_REQUIRED: bool = False
    DATABASE_SSL_CA_FILE: str | None = None
    DATABASE_PASSWORD_SECRET_ARN: str | None = None

    # Seguridad Criptográfica
    SECRET_KEY: str = Field(
        default="insecure_dev_jwt_secret_key_minimum_32_characters_long_2026"
    )
    NULLIFIER_SECRET: str = Field(
        default="insecure_dev_nullifier_secret_key_minimum_32_chars_2026"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    # Usuario Superadministrador inicial (PLATFORM_ADMIN)
    PLATFORM_ADMIN_EMAIL: str = "admin@votoseguro.org"
    PLATFORM_ADMIN_PASSWORD: str = "AdminPlatform2026!"

    # Scheduler autónomo
    RUN_EMBEDDED_SCHEDULER: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 10

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://votoseguro.pages.dev"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Feature flags y configuración para IA Local (Sprint 2 y Sprint 2.5 - Túnel Estático)
    AI_LOCAL_ENABLED: bool = True
    AI_EXTERNAL_ENABLED: bool = True
    NGROK_STATIC_DOMAIN: str = "repackage-remarry-reviving.ngrok-free.dev"
    LLM_BASE_URL: str = "https://repackage-remarry-reviving.ngrok-free.dev/v1"
    LLM_MODEL_NAME: str = "votoseguro-lfm3"
    LLM_TIMEOUT_SECONDS: float = 25.0
    STRICT_NEURAL_MODE: bool = False

    # Gemini External AI (Sprint 3 - IA-E1, IA-E2, IA-E3)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.8-flash")
    GEMINI_TIMEOUT_SECONDS: float = Field(default=20.0)

    # Inspector de Credenciales de Demostración (Sprint 1)
    DEMO_CREDENTIAL_INSPECTOR_ENABLED: bool = True

    # S2-06: Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    # S2-09: Notificaciones SMTP
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "notificaciones@votoseguro.org"

    @model_validator(mode="after")
    def configure_runtime(self):
        if self.DATABASE_PASSWORD_SECRET_ARN and not self.PGHOST:
            raise ValueError("La contraseña administrada por RDS requiere PGHOST.")
        if self.PGHOST:
            if not self.PGUSER or not self.PGPASSWORD:
                raise ValueError("PGUSER y PGPASSWORD son obligatorios con PGHOST.")
            db_url = URL.create("postgresql+asyncpg", username=self.PGUSER,
                password=self.PGPASSWORD, host=self.PGHOST, port=self.PGPORT,
                database=self.PGDATABASE)
            self.DATABASE_URL = db_url.render_as_string(hide_password=False)
            self.SYNC_DATABASE_URL = db_url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
        if self.ENVIRONMENT == "production":
            if self.DEBUG or self.DEMO_CREDENTIAL_INSPECTOR_ENABLED:
                raise ValueError("DEBUG e inspector de credenciales deben estar desactivados en producción.")
            if any(len(s) < 32 or s.startswith("insecure_dev") for s in [self.SECRET_KEY, self.NULLIFIER_SECRET]):
                raise ValueError("Configure secretos de producción independientes de al menos 32 caracteres.")
            if self.SECRET_KEY == self.NULLIFIER_SECRET:
                raise ValueError("Los secretos JWT y nullifier deben ser distintos.")
            if self.PLATFORM_ADMIN_PASSWORD == "AdminPlatform2026!" or len(self.PLATFORM_ADMIN_PASSWORD) < 16:
                raise ValueError("Configure una contraseña inicial de administración de al menos 16 caracteres.")
            if not self.DATABASE_SSL_REQUIRED:
                raise ValueError("La conexión a la base de producción debe verificar TLS.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
