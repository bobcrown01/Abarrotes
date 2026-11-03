"""Endpoints HTTP de inicio y cierre de sesión."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.routes.dependencies import SESSION_COOKIE, AuthServiceDep, CurrentUserDep
from app.schemas.auth import AuthStatusOut, CurrentUserOut, LoginRequest, SetupRequest
from app.services.auth_service import SESSION_HOURS, CurrentUser

router = APIRouter(prefix="/auth", tags=["sesión"])


def _set_session_cookie(response: Response, token: str) -> None:
    """Guarda el token en una cookie que JavaScript no puede leer.

    ``SameSite=Strict`` evita que otra página haga peticiones con la sesión del
    cajero. No lleva ``Secure`` porque el POS se sirve por HTTP dentro de la tienda.

    Args:
        response: Respuesta HTTP.
        token: Token en claro de la sesión.
    """
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        samesite="strict",
        path="/",
    )


@router.get("/status", response_model=AuthStatusOut)
def auth_status(service: AuthServiceDep) -> AuthStatusOut:
    """Indica si falta crear el primer administrador."""
    return AuthStatusOut(needs_setup=service.needs_setup())


@router.post("/setup", response_model=CurrentUserOut, status_code=status.HTTP_201_CREATED)
def setup(data: SetupRequest, response: Response, service: AuthServiceDep) -> CurrentUser:
    """Crea el primer administrador. Responde 409 si ya existe uno."""
    user, token = service.setup_admin(data.username, data.password)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=CurrentUserOut)
def login(data: LoginRequest, response: Response, service: AuthServiceDep) -> CurrentUser:
    """Abre una sesión. Responde 401 si las credenciales fallan y 429 si hay muchos intentos."""
    user, token = service.login(data.username, data.password)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    service: AuthServiceDep,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    """Cierra la sesión actual en el servidor y borra la cookie."""
    service.logout(session_token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=CurrentUserOut)
def me(user: CurrentUserDep) -> CurrentUser:
    """Regresa el usuario de la sesión. Responde 401 si no hay sesión."""
    return user
