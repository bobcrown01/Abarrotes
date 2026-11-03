"""Esquemas Pydantic de usuarios."""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

# bcrypt ignora todo lo que pase de 72 bytes
_BCRYPT_MAX_BYTES = 72

# PIN de cajero: entre 4 y 8 dígitos, para entrar rápido en la caja
_PIN_PATTERN = re.compile(r"^\d{4,8}$")


def is_pin(secret: str) -> bool:
    """Indica si la clave es un PIN numérico corto.

    Args:
        secret: Contraseña o PIN en texto plano.

    Returns:
        ``True`` si son solo dígitos, de 4 a 8.
    """
    return _PIN_PATTERN.fullmatch(secret) is not None


def _fits_bcrypt(value: str) -> str:
    """Rechaza claves que bcrypt truncaría en silencio.

    Args:
        value: Clave en texto plano.

    Returns:
        La misma clave si es válida.

    Raises:
        ValueError: Si pasa de 72 bytes en UTF-8.
    """
    if len(value.encode()) > _BCRYPT_MAX_BYTES:
        raise ValueError("La contraseña no puede pasar de 72 bytes")
    return value


# Clave de administrador: contraseña completa, nunca un PIN
AdminSecret = Annotated[str, Field(min_length=8), AfterValidator(_fits_bcrypt)]


class UserCreate(BaseModel):
    """Datos para dar de alta un usuario.

    ``password`` admite un PIN de 4 a 8 dígitos; el servicio solo lo permite
    para el rol de cajero.
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=4)
    role_id: int = Field(gt=0)

    @field_validator("password")
    @classmethod
    def password_or_pin(cls, value: str) -> str:
        """Acepta una contraseña de 8 caracteres o más, o un PIN.

        Args:
            value: Contraseña o PIN en texto plano.

        Returns:
            La misma clave si es válida.

        Raises:
            ValueError: Si es muy corta y no es un PIN, o si no cabe en bcrypt.
        """
        if len(value) < 8 and not is_pin(value):
            raise ValueError("Usa una contraseña de 8 caracteres o un PIN de 4 a 8 dígitos")
        return _fits_bcrypt(value)


class UserOut(BaseModel):
    """Usuario tal como lo devuelve la API (nunca incluye el hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role_id: int | None
    is_active: bool
