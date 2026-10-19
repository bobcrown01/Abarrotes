"""Endpoints HTTP de ventas."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.models.sale import Sale
from app.routes.dependencies import SaleServiceDep
from app.schemas.sale import PaymentCreate, SaleCreate, SaleItemCreate, SaleOut, SaleSummaryOut

router = APIRouter(tags=["ventas"])


@router.post("/sales", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(data: SaleCreate, service: SaleServiceDep) -> Sale:
    """Abre una venta en estado ``pendiente``."""
    return service.create_sale(data)


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
def cancel_sale(sale_id: int, service: SaleServiceDep) -> Sale:
    """Cancela la venta; si ya estaba pagada regresa el inventario."""
    return service.cancel_sale(sale_id)


@router.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, service: SaleServiceDep) -> Sale:
    """Regresa una venta con partidas y pagos."""
    return service.get_sale(sale_id)


@router.get("/sales", response_model=list[SaleSummaryOut])
def list_sales(
    service: SaleServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Sale]:
    """Lista las ventas más recientes (paginado)."""
    return service.list_sales(limit, offset)
