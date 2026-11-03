"""Endpoints HTTP de ventas."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.models.sale import Sale
from app.routes.dependencies import LOGIN_REQUIRED, CurrentUserDep, SaleServiceDep
from app.schemas.sale import (
    PaymentCreate,
    SaleCreate,
    SaleFilters,
    SaleItemCreate,
    SaleOut,
    SalesSummaryOut,
    SaleSummaryOut,
)

# Todas las operaciones de venta requieren haber iniciado sesión
router = APIRouter(tags=["ventas"], dependencies=[LOGIN_REQUIRED])


@router.post("/sales", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(data: SaleCreate, service: SaleServiceDep, user: CurrentUserDep) -> Sale:
    """Abre una venta en estado ``pendiente``."""
    # El cajero es quien tiene la sesión: no se puede vender a nombre de otro
    return service.create_sale(data.model_copy(update={"user_id": user.id}))


@router.post("/sales/items", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def add_sale_item(data: SaleItemCreate, service: SaleServiceDep) -> Sale:
    """Agrega un producto a la venta con el precio del catálogo."""
    return service.add_item(data)


@router.post("/sales/payments", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def add_payment(data: PaymentCreate, service: SaleServiceDep) -> Sale:
    """Registra un pago; el cambio se calcula en el servidor."""
    return service.add_payment(data)


@router.post("/sales/{sale_id}/close", response_model=SaleOut)
def close_sale(sale_id: int, service: SaleServiceDep) -> Sale:
    """Cierra la venta pagada y descuenta el inventario."""
    return service.close_sale(sale_id)


@router.post("/sales/{sale_id}/cancel", response_model=SaleOut)
def cancel_sale(sale_id: int, service: SaleServiceDep, user: CurrentUserDep) -> Sale:
    """Cancela la venta; si ya estaba pagada regresa el inventario.

    Una venta pagada solo la cancela un rol de administración (403 si no). Una
    pendiente la puede cancelar el cajero: así se limpia un cobro que falló.
    """
    return service.cancel_sale(sale_id, allow_paid=user.can_manage)


# Va antes de /sales/{sale_id}: si no, FastAPI lee "summary" como id y responde 422
@router.get("/sales/summary", response_model=SalesSummaryOut)
def summarize_sales(
    service: SaleServiceDep, filters: Annotated[SaleFilters, Query()]
) -> SalesSummaryOut:
    """Cuenta y suma las ventas pagadas que coinciden con los filtros."""
    count, total = service.summarize_sales(filters)
    return SalesSummaryOut(count=count, total=total)


@router.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, service: SaleServiceDep) -> Sale:
    """Regresa una venta con partidas y pagos."""
    return service.get_sale(sale_id)


@router.get("/sales", response_model=list[SaleSummaryOut])
def list_sales(service: SaleServiceDep, filters: Annotated[SaleFilters, Query()]) -> Sequence[Sale]:
    """Lista las ventas más recientes, por estado, folio y rango de fechas (paginado)."""
    return service.list_sales(filters)
