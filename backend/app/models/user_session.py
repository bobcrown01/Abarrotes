"""Modelo ORM de sesiones de usuario (login del POS)."""

from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserSession(Base):
    """Sesión abierta tras un login correcto.

    Se guarda en la base para poder cerrarla desde el servidor. Solo se
    almacena el hash del token: quien lea la tabla no puede usar las sesiones.
    """

    __tablename__ = "user_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
