"""Endpoints HTTP de usuarios."""

from collections.abc import Sequence

from fastapi import APIRouter, status

from app.models.user import User
from app.routes.dependencies import LOGIN_REQUIRED, MANAGER_REQUIRED, UserServiceDep
from app.schemas.user import UserCreate, UserOut

# Ver la lista requiere sesión; dar de alta usuarios, un rol de administración
router = APIRouter(tags=["usuarios"], dependencies=[LOGIN_REQUIRED])


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[MANAGER_REQUIRED],
)
def create_user(data: UserCreate, service: UserServiceDep) -> User:
    """Da de alta un usuario. Responde 409 si el nombre ya existe."""
    return service.create_user(data)


@router.get("/users", response_model=list[UserOut])
def list_users(service: UserServiceDep) -> Sequence[User]:
    """Lista los usuarios (sin hashes de contraseña)."""
    return service.list_users()
