"""Cálculo de los reportes de ventas."""

from decimal import ROUND_HALF_UP, Decimal

from app.repositories.report_repository import ReportRepository
from app.schemas.common import DateRangeFilters
from app.schemas.report import IdleProductOut, ProductSalesOut, SalesReportOut

_CENT = Decimal("0.01")
TOP_LIMIT = 10
IDLE_LIMIT = 20


class ReportService:
    """Arma el resumen de ventas de un periodo."""

    def __init__(self, reports: ReportRepository) -> None:
        """Crea el servicio.

        Args:
            reports: Repositorio de reportes.
        """
        self._reports = reports

    def sales_report(self, filters: DateRangeFilters) -> SalesReportOut:
        """Calcula totales, ganancia, lo más vendido y lo que no se movió.

        Args:
            filters: Rango de fechas.
        """
        count, total = self._reports.sales_totals(filters)
        revenue, cost, without_cost = self._reports.revenue_and_cost(filters)
        idle, idle_total = self._reports.idle_products(filters, IDLE_LIMIT)
        # Sin ventas el promedio es cero, no una división entre cero
        average = (total / count).quantize(_CENT, rounding=ROUND_HALF_UP) if count else Decimal("0")

        return SalesReportOut(
            sales_count=count,
            sales_total=total,
            average_ticket=average,
            profit=(revenue - cost).quantize(_CENT, rounding=ROUND_HALF_UP),
            revenue_without_cost=without_cost,
            top_products=[
                ProductSalesOut(product_id=p, name=name, quantity=quantity, total=amount)
                for p, name, quantity, amount in self._reports.top_products(filters, TOP_LIMIT)
            ],
            idle_products=[IdleProductOut(product_id=p, name=name) for p, name in idle],
            idle_total=idle_total,
        )
