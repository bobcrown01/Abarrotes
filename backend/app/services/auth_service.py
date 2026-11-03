"""Inicio de sesión: credenciales, sesiones y permisos por rol."""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import status

from app.core.exceptions import AppError, ConflictError
from app.core.unit_of_work import UnitOfWork
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.user_repository import RoleRepository, SessionRepository, UserRepository
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

SESSION_HOURS = 12  # Alcanza para un turno largo; después hay que volver a entrar
ADMIN_ROLE = "admin"
MANAGER_ROLES = frozenset({ADMIN_ROLE, "supervisor"})  # Pueden cancelar, ajustar y cambiar precios

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 5

# Hash de relleno: un usuario inexistente tarda lo mismo que una clave incorrecta,
# para que el tiempo de respuesta no revele qué nombres existen
_DUMMY_HASH = hash_password("relleno-para-igualar-el-tiempo")


class NotAuthenticatedError(AppError):
    """No hay una sesión válida."""

    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail: str = "Inicia sesión para continuar") -> None:
        """Crea el error.

        Args:
            detail: Mensaje para el usuario.
        """
        super().__init__(detail)


class TooManyAttemptsError(AppError):
    """Demasiados intentos fallidos con este usuario."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__(f"Demasiados intentos. Espera {LOCK_MINUTES} minutos e inténtalo de nuevo")


class SetupAlreadyDoneError(ConflictError):
    """Ya existe un administrador: la configuración inicial está cerrada."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("El sistema ya tiene un administrador")


class SetupRoleMissingError(AppError):
    """La base no tiene el rol de administrador (falta insertar_roles.sql)."""

    def __init__(self) -> None:
        """Crea el error con su mensaje para el usuario."""
        super().__init__("Falta el rol de administrador en la base de datos")


@dataclass(frozen=True)
class CurrentUser:
    """Quien hace la petición.

    Attributes:
        id: Id del usuario.
        username: Nombre de usuario.
        role: Nombre del rol, o ``None`` si no tiene.
    """

    id: int
    username: str
    role: str | None

    @property
    def can_manage(self) -> bool:
        """Indica si puede cancelar ventas, ajustar inventario y cambiar el catálogo."""
        return self.role in MANAGER_ROLES


class LoginThrottle:
    """Cuenta los intentos fallidos por usuario y lo bloquea unos minutos.

    Vive en memoria: el backend corre con un solo worker y, si se reinicia, lo
    peor que pasa es que el contador vuelve a cero.
    """

    def __init__(self) -> None:
        """Crea el contador vacío."""
        self._failures: dict[str, tuple[int, datetime]] = {}

    def is_locked(self, username: str, now: datetime) -> bool:
        """Indica si el usuario sigue bloqueado.

        Args:
            username: Nombre tecleado (exista o no).
            now: Momento actual.
        """
        count, last_failure = self._failures.get(username, (0, now))
        if count < MAX_FAILED_ATTEMPTS:
            return False
        if now - last_failure >= timedelta(minutes=LOCK_MINUTES):
            del self._failures[username]
            return False
        return True

    def record_failure(self, username: str, now: datetime) -> None:
        """Suma un intento fallido.

        Args:
            username: Nombre tecleado.
            now: Momento actual.
        """
        count, _ = self._failures.get(username, (0, now))
        self._failures[username] = (count + 1, now)

    def reset(self, username: str) -> None:
        """Olvida los fallos tras un login correcto.

        Args:
            username: Nombre de usuario.
        """
        self._failures.pop(username, None)


login_throttle = LoginThrottle()


def _utc_now() -> datetime:
    """Regresa la hora actual en UTC sin zona, igual que guarda TIMESTAMP en la base."""
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    """Calcula el hash con el que se guarda un token de sesión.

    SHA-256 es suficiente aquí: el token ya es aleatorio y largo, no una clave
    elegida por una persona.

    Args:
        token: Token en claro de la cookie.
    """
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Casos de uso de inicio de sesión."""

    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        sessions: SessionRepository,
        uow: UnitOfWork,
        throttle: LoginThrottle = login_throttle,
    ) -> None:
        """Crea el servicio.

        Args:
            users: Repositorio de usuarios.
            roles: Repositorio de roles.
            sessions: Repositorio de sesiones.
            uow: Transacción de la petición.
            throttle: Contador de intentos fallidos.
        """
        self._users = users
        self._roles = roles
        self._sessions = sessions
        self._uow = uow
        self._throttle = throttle

    def needs_setup(self) -> bool:
        """Indica si falta crear el primer administrador."""
        return not self._users.active_admin_exists()

    def setup_admin(self, username: str, password: str) -> tuple[CurrentUser, str]:
        """Crea el primer administrador y le abre sesión.

        Args:
            username: Nombre del administrador.
            password: Contraseña en texto plano.

        Returns:
            El usuario y el token en claro para la cookie.

        Raises:
            SetupAlreadyDoneError: Si ya existe un administrador activo.
            SetupRoleMissingError: Si la base no tiene el rol ``admin``.
        """
        if not self.needs_setup():
            raise SetupAlreadyDoneError()
        role = self._roles.get_by_name(ADMIN_ROLE)
        if role is None:
            raise SetupRoleMissingError()
        if self._users.username_exists(username):
            raise ConflictError("El usuario ya existe")

        user = self._users.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role_id=role.id,
                is_active=True,
            )
        )
        logger.warning("Administrador inicial creado: %s", user.username)
        return CurrentUser(user.id, user.username, role.name), self._open_session(user.id)

    def login(self, username: str, password: str) -> tuple[CurrentUser, str]:
        """Valida las credenciales y abre una sesión.

        Args:
            username: Nombre de usuario.
            password: Contraseña o PIN en texto plano.

        Returns:
            El usuario y el token en claro para la cookie.

        Raises:
            TooManyAttemptsError: Si el usuario está bloqueado por intentos fallidos.
            NotAuthenticatedError: Si las credenciales no son válidas.
        """
        now = _utc_now()
        if self._throttle.is_locked(username, now):
            raise TooManyAttemptsError()

        user = self._users.get_by_username(username)
        # Siempre se verifica un hash, exista o no el usuario
        valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if user is None or not valid or not user.is_active:
            self._throttle.record_failure(username, now)
            logger.warning("Login fallido para %r", username)
            # El mismo mensaje en todos los casos: no revela qué nombres existen
            raise NotAuthenticatedError("Usuario o contraseña incorrectos")

        self._throttle.reset(username)
        role = self._roles.get(user.role_id)
        return (
            CurrentUser(user.id, user.username, role.name if role else None),
            self._open_session(user.id),
        )

    def logout(self, token: str | None) -> None:
        """Cierra la sesión del token, si existe.

        Args:
            token: Token en claro de la cookie.
        """
        if not token:
            return
        session = self._sessions.get(_hash_token(token))
        if session is not None:
            self._sessions.delete(session)
            self._uow.commit()

    def authenticate(self, token: str | None) -> CurrentUser:
        """Resuelve el usuario de una cookie de sesión.

        Args:
            token: Token en claro de la cookie.

        Returns:
            El usuario de la sesión.

        Raises:
            NotAuthenticatedError: Si no hay sesión válida o el usuario se desactivó.
        """
        if not token:
            raise NotAuthenticatedError()

        session = self._sessions.get(_hash_token(token))
        if session is None or session.expires_at <= _utc_now():
            raise NotAuthenticatedError()

        user = self._users.get(session.user_id)
        if user is None or not user.is_active:
            raise NotAuthenticatedError()

        role = self._roles.get(user.role_id)
        return CurrentUser(user.id, user.username, role.name if role else None)

    def _open_session(self, user_id: int) -> str:
        """Crea una sesión, limpia las vencidas y confirma la transacción.

        Args:
            user_id: Dueño de la sesión.

        Returns:
            El token en claro; en la base solo queda su hash.
        """
        token = secrets.token_urlsafe(32)
        now = _utc_now()
        self._sessions.delete_expired(now)
        self._sessions.add(
            UserSession(
                token_hash=_hash_token(token),
                user_id=user_id,
                expires_at=now + timedelta(hours=SESSION_HOURS),
            )
        )
        self._uow.commit()
        return token
