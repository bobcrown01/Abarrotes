"""Esquemas Pydantic del inicio de sesión."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import AdminSecret


class LoginRequest(BaseModel):
    """Credenciales que envía la pantalla de login."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    # Máximo por bcrypt: una contraseña más larga nunca puede ser válida
    password: str = Field(min_length=1, max_length=72)


class SetupRequest(BaseModel):
    """Datos del primer administrador, cuando aún no existe ninguno."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: AdminSecret


class CurrentUserOut(BaseModel):
    """Usuario con la sesión abierta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str | None
    can_manage: bool


class AuthStatusOut(BaseModel):
    """Lo que necesita saber la pantalla de login antes de mostrarse."""

    needs_setup: bool
