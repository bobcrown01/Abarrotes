"""Endpoints HTTP de apertura y corte de caja."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, status

from app.core.config import get_settings
from app.routes.dependencies import (
    LOGIN_REQUIRED,
    MANAGER_REQUIRED,
    CashServiceDep,
    CurrentUserDep,
    InventoryServiceDep,
)
from app.schemas.cash import CashClose, CashCurrentOut, CashOpen, CashSessionOut
from app.services.cash_service import CashSummary
from app.telegram.notifications import cash_report_text, send_text

# Cualquier usuario con sesión abre y cierra caja; el historial es de administración
router = APIRouter(prefix="/cash", tags=["caja"], dependencies=[LOGIN_REQUIRED])


@router.get("/current", response_model=CashCurrentOut)
def current_cash(service: CashServiceDep, user: CurrentUserDep) -> dict[str, CashSummary | None]:
    """Regresa la caja abierta o ``null``. A un cajero no le muestra el efectivo esperado."""
    session = service.current()
    if session is not None and not user.can_manage:
        session = session.hide_expected()
    return {"session": session}


@router.post("/open", response_model=CashSessionOut, status_code=status.HTTP_201_CREATED)
def open_cash(data: CashOpen, service: CashServiceDep, user: CurrentUserDep) -> CashSummary:
    """Abre la caja con su fondo inicial. Responde 409 si ya está abierta."""
    session = service.open_cash(data, user.id)
    return session if user.can_manage else session.hide_expected()


@router.post("/close", response_model=CashSessionOut)
def close_cash(
    data: CashClose,
    request: Request,
    background: BackgroundTasks,
    service: CashServiceDep,
    inventory: InventoryServiceDep,
    user: CurrentUserDep,
) -> CashSummary:
    """Hace el corte y regresa el resultado. Responde 409 si la caja está cerrada.

    Si el bot de Telegram está activo y hay ``TELEGRAM_CHAT_ID``, manda el corte
    y los productos por surtir después de responder.
    """
    summary = service.close_cash(data, user.id)

    bot = getattr(request.app.state, "telegram_bot", None)
    chat_id = get_settings().telegram_chat_id
    if bot is not None and chat_id is not None:
        text = cash_report_text(summary, user.username, inventory.low_stock())
        background.add_task(send_text, bot, chat_id, text)
    return summary


@router.get("/sessions", response_model=list[CashSessionOut], dependencies=[MANAGER_REQUIRED])
def list_cash_sessions(
    service: CashServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[CashSummary]:
    """Lista los cortes hechos, los más recientes primero."""
    return service.history(limit, offset)
