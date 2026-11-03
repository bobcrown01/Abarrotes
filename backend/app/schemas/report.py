"""Esquemas Pydantic de los reportes."""

from pydantic import BaseModel

from app.schemas.common import DecimalOut


class ProductSalesOut(BaseModel):
    """Lo vendido de un producto en el periodo."""

    product_id: int
    name: str
    quantity: DecimalOut
    total: DecimalOut


class IdleProductOut(BaseModel):
    """Producto activo que no se vendió en el periodo."""

    product_id: int
    name: str


class SalesReportOut(BaseModel):
    """Resumen de ventas del periodo.

    ``profit`` solo considera lo vendido con costo capturado; ``revenue_without_cost``
    dice cuánta venta quedó fuera de ese cálculo para no presumir una ganancia falsa.
    """

    sales_count: int
    sales_total: DecimalOut
    average_ticket: DecimalOut
    profit: DecimalOut
    revenue_without_cost: DecimalOut
    top_products: list[ProductSalesOut]
    idle_products: list[IdleProductOut]
    idle_total: int
