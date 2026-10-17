"""Construcción de servicios por petición (inyección de dependencias de FastAPI).

Es el único lugar donde se conectan servicios con repositorios concretos; las
pruebas sustituyen ``get_db`` y todo lo demás se arma igual.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import CategoryRepository, ProductRepository
from app.repositories.sale_repository import CustomerRepository, SaleRepository
from app.repositories.user_repository import RoleRepository, UserRepository
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService
from app.services.sale_service import SaleService
from app.services.user_service import UserService

DbSession = Annotated[Session, Depends(get_db)]


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
        inventory=_inventory_service(db),
        uow=db,
    )


def get_user_service(db: DbSession) -> UserService:
    """Dependencia: servicio de usuarios de la petición."""
    return UserService(UserRepository(db), RoleRepository(db), uow=db)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
SaleServiceDep = Annotated[SaleService, Depends(get_sale_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
