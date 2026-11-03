"""Endpoints HTTP de inventario.

Importante: ``/inventory/movements`` va antes que ``/inventory/{product_id}``;
si no, FastAPI intenta leer "movements" como id y responde 422.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.routes.dependencies import (
    LOGIN_REQUIRED,
    MANAGER_REQUIRED,
    InventoryServiceDep,
    require_manager,
)
from app.schemas.inventory import (
    InventoryMovementCreate,
    InventoryMovementOut,
    MinStockUpdate,
    MovementFilters,
    MovementListOut,
    ProductMovementOut,
    StockFilters,
    StockOut,
)
from app.services.auth_service import CurrentUser
from app.services.inventory_service import MovementView, RecordedMovement, StockView

# Consultar requiere sesión; registrar movimientos, un rol de administración
router = APIRouter(tags=["inventario"], dependencies=[LOGIN_REQUIRED])


@router.post(
    "/inventory/movements",
    response_model=InventoryMovementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_movement(
    data: InventoryMovementCreate,
    service: InventoryServiceDep,
    user: Annotated[CurrentUser, Depends(require_manager)],
) -> RecordedMovement:
    """Registra una entrada, salida o ajuste de inventario.

    Responde 404 si el producto no existe y 409 si una salida deja
    existencias negativas.
    """
    # El responsable es quien tiene la sesión, no lo que diga la petición
    return service.record_movement(data.model_copy(update={"user_id": user.id}))


@router.put(
    "/inventory/{product_id}/min-stock", response_model=StockOut, dependencies=[MANAGER_REQUIRED]
)
def set_min_stock(product_id: int, data: MinStockUpdate, service: InventoryServiceDep) -> StockView:
    """Define desde cuánto un producto se marca "Por surtir". 404 si no existe."""
    return service.set_min_stock(product_id, data.min_stock)


@router.get("/inventory", response_model=list[StockOut])
def list_stock(
    service: InventoryServiceDep, filters: Annotated[StockFilters, Query()]
) -> list[StockView]:
    """Lista existencias por categoría y con/sin stock, ordenadas por producto."""
    return service.list_stock(filters)


@router.get("/inventory/movements", response_model=list[MovementListOut])
def list_movements(
    service: InventoryServiceDep, filters: Annotated[MovementFilters, Query()]
) -> list[MovementView]:
    """Historial de movimientos por producto, tipo, usuario y rango de fechas."""
    return service.list_movements(filters)


@router.get("/inventory/{product_id}", response_model=StockOut)
def get_stock(product_id: int, service: InventoryServiceDep) -> StockView:
    """Existencias de un producto. Responde 404 si no lleva inventario."""
    return service.get_stock(product_id)


@router.get("/inventory/{product_id}/movements", response_model=list[ProductMovementOut])
def list_product_movements(
    product_id: int,
    service: InventoryServiceDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MovementView]:
    """Historial de un producto, lo más reciente primero. 404 si no existe."""
    return service.list_product_movements(product_id, limit, offset)
