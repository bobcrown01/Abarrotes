"""Acceso a datos de usuarios y roles."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession


class UserRepository:
    """Consultas y escrituras sobre ``users``.

    No confirma transacciones: eso le toca al servicio.
    """

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def list_all(self) -> Sequence[User]:
        """Regresa todos los usuarios ordenados por nombre de usuario."""
        return self._db.scalars(select(User).order_by(User.username)).all()

    def exists(self, user_id: int) -> bool:
        """Indica si existe un usuario con ese id.

        Args:
            user_id: Id del usuario.
        """
        return self._db.get(User, user_id) is not None

    def username_exists(self, username: str) -> bool:
        """Indica si el nombre de usuario ya está tomado.

        Args:
            username: Nombre de usuario.
        """
        statement = select(User.id).where(User.username == username).limit(1)
        return self._db.scalar(statement) is not None

    def add(self, user: User) -> User:
        """Inserta un usuario y lo regresa con su id.

        Args:
            user: Usuario nuevo.
        """
        self._db.add(user)
        self._db.flush()
        return user

    def get(self, user_id: int) -> User | None:
        """Regresa un usuario por id, o ``None`` si no existe.

        Args:
            user_id: Id del usuario.
        """
        return self._db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        """Regresa un usuario por nombre, o ``None`` si no existe.

        Args:
            username: Nombre de usuario.
        """
        return self._db.scalar(select(User).where(User.username == username))

    def active_admin_exists(self) -> bool:
        """Indica si ya hay un administrador activo (define si falta la configuración inicial)."""
        statement = (
            select(User.id)
            .join(Role, User.role_id == Role.id)
            .where(Role.name == "admin", User.is_active.is_(True))
            .limit(1)
        )
        return self._db.scalar(statement) is not None


class SessionRepository:
    """Consultas y escrituras sobre ``user_sessions``."""

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def add(self, session: UserSession) -> None:
        """Guarda una sesión nueva.

        Args:
            session: Sesión con el hash de su token.
        """
        self._db.add(session)

    def get(self, token_hash: str) -> UserSession | None:
        """Busca una sesión por el hash de su token.

        Args:
            token_hash: SHA-256 del token de la cookie.
        """
        return self._db.get(UserSession, token_hash)

    def delete(self, session: UserSession) -> None:
        """Borra una sesión (cierre de sesión o vencimiento).

        Args:
            session: Sesión a borrar.
        """
        self._db.delete(session)

    def delete_expired(self, now: datetime) -> None:
        """Borra las sesiones vencidas para que la tabla no crezca sin límite.

        Args:
            now: Momento actual en UTC, sin zona.
        """
        self._db.execute(delete(UserSession).where(UserSession.expires_at <= now))


class RoleRepository:
    """Consultas sobre ``roles``."""

    def __init__(self, db: Session) -> None:
        """Crea el repositorio.

        Args:
            db: Sesión activa de SQLAlchemy.
        """
        self._db = db

    def exists(self, role_id: int) -> bool:
        """Indica si existe un rol con ese id.

        Args:
            role_id: Id del rol.
        """
        return self._db.get(Role, role_id) is not None

    def get(self, role_id: int | None) -> Role | None:
        """Regresa un rol por id, o ``None`` si no tiene o no existe.

        Args:
            role_id: Id del rol.
        """
        return self._db.get(Role, role_id) if role_id is not None else None

    def get_by_name(self, name: str) -> Role | None:
        """Regresa un rol por nombre, o ``None`` si no existe.

        Args:
            name: Nombre del rol, p. ej. ``admin``.
        """
        return self._db.scalar(select(Role).where(Role.name == name))
