"""Reglas de negocio de usuarios."""

import logging
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, ConflictError
from app.core.unit_of_work import UnitOfWork
from app.models.user import User
from app.repositories.user_repository import RoleRepository, UserRepository
from app.schemas.user import UserCreate
from app.utils.security import hash_password

logger = logging.getLogger(__name__)


class RoleNotFoundError(AppError):
    """El rol indicado no existe."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El rol no existe")


class UsernameTakenError(ConflictError):
    """El nombre de usuario ya está registrado."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El usuario ya existe")


class UserService:
    """Alta y consulta de usuarios."""

    def __init__(self, users: UserRepository, roles: RoleRepository, uow: UnitOfWork) -> None:
        """Crea el servicio.

        Args:
            users: Repositorio de usuarios.
            roles: Repositorio de roles.
            uow: Transacción de la petición.
        """
        self._users = users
        self._roles = roles
        self._uow = uow

    def list_users(self) -> Sequence[User]:
        """Regresa todos los usuarios."""
        return self._users.list_all()

    def create_user(self, data: UserCreate) -> User:
        """Da de alta un usuario guardando solo el hash de su contraseña.

        Args:
            data: Datos validados por Pydantic.

        Raises:
            RoleNotFoundError: Si el rol no existe.
            UsernameTakenError: Si el nombre de usuario ya está tomado.
        """
        if not self._roles.exists(data.role_id):
            raise RoleNotFoundError()
        if self._users.username_exists(data.username):
            raise UsernameTakenError()

        try:
            user = self._users.add(
                User(
                    username=data.username,
                    password_hash=hash_password(data.password),
                    role_id=data.role_id,
                    is_active=True,
                )
            )
            self._uow.commit()
        except IntegrityError as exc:
            # Dos altas simultáneas con el mismo nombre: gana la primera
            self._uow.rollback()
            logger.warning("Alta de usuario rechazada por la base: %s", exc.orig)
            raise UsernameTakenError() from exc

        logger.info("Usuario creado id=%s username=%s", user.id, user.username)
        return user
