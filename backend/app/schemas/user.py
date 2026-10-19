"""Esquemas Pydantic de usuarios."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

# bcrypt ignora todo lo que pase de 72 bytes
_BCRYPT_MAX_BYTES = 72


class UserCreate(BaseModel):
    """Datos para dar de alta un usuario."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8)
    role_id: int = Field(gt=0)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        """Rechaza contraseñas que bcrypt truncaría en silencio.

        Args:
            value: Contraseña en texto plano.

        Returns:
            La misma contraseña si es válida.

        Raises:
            ValueError: Si pasa de 72 bytes en UTF-8.
        """
        if len(value.encode()) > _BCRYPT_MAX_BYTES:
            raise ValueError("La contraseña no puede pasar de 72 bytes")
        return value


class UserOut(BaseModel):
    """Usuario tal como lo devuelve la API (nunca incluye el hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role_id: int | None
    is_active: bool
