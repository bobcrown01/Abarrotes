"""Endpoints HTTP de reportes."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.routes.dependencies import MANAGER_REQUIRED, ReportServiceDep
from app.schemas.common import DateRangeFilters
from app.schemas.report import SalesReportOut

# La ganancia y los costos son solo para roles de administración
router = APIRouter(prefix="/reports", tags=["reportes"], dependencies=[MANAGER_REQUIRED])


@router.get("/sales", response_model=SalesReportOut)
def sales_report(
    service: ReportServiceDep, filters: Annotated[DateRangeFilters, Query()]
) -> SalesReportOut:
    """Resumen del periodo: totales, ganancia, lo más vendido y lo que no se movió."""
    return service.sales_report(filters)
