"""Motor de base de datos, sesiones y clase base de los modelos ORM."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

# create_engine no abre conexiones hasta la primera consulta
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Clase base de todos los modelos ORM."""


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI que entrega una sesión por petición.

    Yields:
        Sesión de SQLAlchemy que se cierra al terminar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
