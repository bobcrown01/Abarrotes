"""Configuración de la aplicación leída desde variables de entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración del backend.

    Attributes:
        database_url: URL de conexión de SQLAlchemy (``DATABASE_URL``).
        app_env: Entorno de ejecución, p. ej. ``production`` o ``development``.
        log_level: Nivel mínimo de los logs (``LOG_LEVEL``).
        db_pool_size: Conexiones permanentes del pool. Bajo a propósito para
            la Raspberry Pi Zero 2 W.
        db_max_overflow: Conexiones extra permitidas en picos.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_env: str = "production"
    log_level: str = "INFO"
    db_pool_size: int = 3
    db_max_overflow: int = 2


@lru_cache
def get_settings() -> Settings:
    """Regresa la configuración, cargada una sola vez por proceso.

    Returns:
        Instancia compartida de :class:`Settings`.
    """
    return Settings()
