"""Endpoints HTTP de inventario."""

from fastapi import APIRouter, status

from app.routes.dependencies import InventoryServiceDep
from app.schemas.inventory import InventoryMovementCreate, InventoryMovementOut
from app.services.inventory_service import RecordedMovement

router = APIRouter(tags=["inventario"])


@router.post(
    "/inventory/movements",
    response_model=InventoryMovementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_movement(
    data: InventoryMovementCreate, service: InventoryServiceDep
) -> RecordedMovement:
    """Registra una entrada, salida o ajuste de inventario.

    Responde 404 si el producto no existe y 409 si una salida deja
    existencias negativas.
    """
    return service.record_movement(data)
