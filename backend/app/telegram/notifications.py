"""Avisos que el POS manda por Telegram (corte de caja y productos por surtir)."""

import logging
from collections.abc import Sequence
from decimal import Decimal

from telegram.error import TelegramError
from telegram.ext import Application

from app.services.cash_service import CashSummary
from app.services.inventory_service import StockView

logger = logging.getLogger(__name__)

MAX_LISTED_PRODUCTS = 20  # Un mensaje largo en el teléfono ya no se lee


def _money(value: Decimal | None) -> str:
    """Formatea un importe como en el ticket: $1,234.50."""
    return f"${value or 0:,.2f}"


def _quantity(value: Decimal) -> str:
    """Formatea una cantidad sin ceros de más: 3 en vez de 3.000."""
    return f"{value.normalize():f}"


def cash_report_text(summary: CashSummary, cashier: str, low_stock: Sequence[StockView]) -> str:
    """Arma el mensaje del corte de caja.

    Args:
        summary: Corte recién hecho.
        cashier: Quien hizo el corte.
        low_stock: Productos agotados o por surtir.

    Returns:
        Texto listo para enviar.
    """
    difference = summary.difference or Decimal("0")
    if difference == 0:
        result = "Cuadra"
    else:
        result = f"{'Faltante' if difference < 0 else 'Sobrante'} {_money(abs(difference))}"

    lines = [
        f"Corte de caja #{summary.id}",
        f"Hizo el corte: {cashier}",
        f"Ventas: {summary.sales_count or 0} · {_money(summary.sales_total)}",
        f"Efectivo esperado: {_money(summary.expected_cash)}",
        f"Efectivo contado: {_money(summary.counted_amount)}",
        f"Resultado: {result}",
    ]
    if summary.notes:
        lines.append(f"Notas: {summary.notes}")

    if low_stock:
        lines += ["", f"Por surtir ({len(low_stock)}):"]
        lines += [
            f"- {s.product_name}: quedan {_quantity(s.quantity)}"
            for s in low_stock[:MAX_LISTED_PRODUCTS]
        ]
        if len(low_stock) > MAX_LISTED_PRODUCTS:
            lines.append(f"... y {len(low_stock) - MAX_LISTED_PRODUCTS} más")
    return "\n".join(lines)


async def send_text(bot: Application, chat_id: int, text: str) -> None:
    """Envía un aviso sin interrumpir el POS si Telegram falla.

    Se ejecuta después de responder la petición: el corte ya quedó guardado
    aunque el mensaje no llegue.

    Args:
        bot: Aplicación del bot ya iniciada.
        chat_id: Chat que recibe los avisos.
        text: Mensaje.
    """
    try:
        await bot.bot.send_message(chat_id=chat_id, text=text)
    except TelegramError as exc:
        # Solo el tipo de error: el mensaje podría incluir el token
        logger.error("No se pudo enviar el aviso de Telegram: %s", type(exc).__name__)
