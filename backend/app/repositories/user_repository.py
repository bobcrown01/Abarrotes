"""Acceso a datos de usuarios y roles."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User


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
