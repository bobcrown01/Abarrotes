"""Construcción de servicios por petición (inyección de dependencias de FastAPI).

Es el único lugar donde se conectan servicios con repositorios concretos; las
pruebas sustituyen ``get_db`` y todo lo demás se arma igual.
"""

from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.core.internal_auth import INTERNAL_TOKEN_HEADER, is_internal_token
from app.database import get_db
from app.repositories.cash_repository import CashRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import CategoryRepository, ProductRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.sale_repository import CustomerRepository, SaleRepository
from app.repositories.user_repository import RoleRepository, SessionRepository, UserRepository
from app.services.auth_service import AuthService, CurrentUser
from app.services.cash_service import CashService
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService
from app.services.report_service import ReportService
from app.services.sale_service import SaleService
from app.services.user_service import UserService

DbSession = Annotated[Session, Depends(get_db)]

SESSION_COOKIE = "pos_session"

# Identidad del bot de Telegram: no es una fila de ``users`` y solo puede leer
INTERNAL_USER = CurrentUser(id=0, username="sistema", role=None)


def get_product_service(db: DbSession) -> ProductService:
    """Dependencia: servicio de productos de la petición."""
    return ProductService(ProductRepository(db), CategoryRepository(db))


def _inventory_service(db: Session) -> InventoryService:
    """Arma el servicio de inventario sobre una sesión."""
    return InventoryService(
        InventoryRepository(db), ProductRepository(db), UserRepository(db), uow=db
    )


def get_inventory_service(db: DbSession) -> InventoryService:
    """Dependencia: servicio de inventario de la petición."""
    return _inventory_service(db)


def get_sale_service(db: DbSession) -> SaleService:
    """Dependencia: servicio de ventas de la petición."""
    return SaleService(
        SaleRepository(db),
        ProductRepository(db),
        UserRepository(db),
        CustomerRepository(db),
        cash=CashRepository(db),
        inventory=_inventory_service(db),
        uow=db,
    )


def get_user_service(db: DbSession) -> UserService:
    """Dependencia: servicio de usuarios de la petición."""
    return UserService(UserRepository(db), RoleRepository(db), uow=db)


def get_auth_service(db: DbSession) -> AuthService:
    """Dependencia: servicio de inicio de sesión de la petición."""
    return AuthService(UserRepository(db), RoleRepository(db), SessionRepository(db), uow=db)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
SaleServiceDep = Annotated[SaleService, Depends(get_sale_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_cash_service(db: DbSession) -> CashService:
    """Dependencia: servicio de caja de la petición."""
    return CashService(CashRepository(db), uow=db)


CashServiceDep = Annotated[CashService, Depends(get_cash_service)]


def get_customer_service(db: DbSession) -> CustomerService:
    """Dependencia: servicio de clientes de la petición."""
    return CustomerService(CustomerRepository(db), CashRepository(db), uow=db)


CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]


def get_report_service(db: DbSession) -> ReportService:
    """Dependencia: servicio de reportes de la petición."""
    return ReportService(ReportRepository(db))


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


def get_current_user(
    request: Request,
    service: AuthServiceDep,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    internal_token: Annotated[str | None, Header(alias=INTERNAL_TOKEN_HEADER)] = None,
) -> CurrentUser:
    """Dependencia: usuario que hace la petición, según su cookie de sesión.

    El bot de Telegram corre dentro del mismo proceso y consulta la API sin
    cookie: se identifica con un token que solo existe en memoria y solo le
    sirve para leer.

    Raises:
        NotAuthenticatedError: Si no hay una sesión válida.
    """
    if internal_token and request.method == "GET" and is_internal_token(internal_token):
        return INTERNAL_USER
    return service.authenticate(session_token)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_manager(user: CurrentUserDep) -> CurrentUser:
    """Dependencia: exige un rol con permiso de administrar.

    Raises:
        ForbiddenError: Si el usuario es, por ejemplo, un cajero.
    """
    if not user.can_manage:
        raise ForbiddenError()
    return user


# Se agregan al router o a la ruta para protegerla
LOGIN_REQUIRED = Depends(get_current_user)
MANAGER_REQUIRED = Depends(require_manager)
