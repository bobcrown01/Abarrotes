"""Bot de Telegram del POS: comandos de consulta para el dueño de la tienda."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters,
)

from app.core.config import get_settings
from app.core.internal_auth import internal_headers


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a /start con un saludo.

    Args:
        update: Mensaje recibido de Telegram.
        context: Contexto del bot (no se usa).
    """
    print("TELEGRAM: recibi /start", flush=True)
    await update.message.reply_text("¡Hola! Soy el bot de tu sistema de abarrotes.")


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a /estado confirmando que el sistema está en línea.

    Args:
        update: Mensaje recibido de Telegram.
        context: Contexto del bot (no se usa).
    """
    await update.message.reply_text("El sistema de abarrotes está funcionando.")


async def productos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a /productos con cuántos productos hay activos e inactivos.

    Args:
        update: Mensaje recibido de Telegram.
        context: Contexto del bot (no se usa).
    """
    try:
        # Con login activo, el bot se identifica con el token interno (solo lectura)
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8000", timeout=5, headers=internal_headers()
        ) as client:
            response = await client.get("/api/products")
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        await update.message.reply_text("No se pudieron consultar los productos.")
        return

    if not isinstance(data, list) or not all(
        isinstance(product, dict) and isinstance(product.get("is_active"), bool) for product in data
    ):
        await update.message.reply_text("La API devolvió una lista de productos inválida.")
        return

    active_count = sum(product["is_active"] for product in data)
    inactive_count = len(data) - active_count
    await update.message.reply_text(
        f"Productos dados de alta: {len(data)} "
        f"(activos: {active_count}, inactivos: {inactive_count})."
    )


def configurar_bot(token: str, chat_id: int | None = None) -> Application:
    """Crea el bot y registra sus comandos.

    Args:
        token: Token del bot que da BotFather.
        chat_id: Si se indica, el bot solo responde en ese chat.

    Returns:
        La aplicación del bot lista para iniciarse.
    """
    bot = Application.builder().token(token).build()

    # Con TELEGRAM_CHAT_ID, el bot solo contesta en ese chat: las ventas no
    # quedan a la vista de cualquiera que encuentre el bot
    solo_tienda = filters.Chat(chat_id) if chat_id is not None else None

    bot.add_handler(CommandHandler("start", start, filters=solo_tienda))
    bot.add_handler(CommandHandler("estado", estado, filters=solo_tienda))
    bot.add_handler(CommandHandler("productos", productos, filters=solo_tienda))
    bot.add_handler(CommandHandler("ventas", ventas, filters=solo_tienda))

    return bot


def fecha_tienda(valor: str) -> date:
    """Día en la tienda de una fecha de la API.

    La base guarda la hora UTC sin zona; a las 6 p. m. en México ya es el día
    siguiente en UTC. Se convierte a la zona de la tienda antes de comparar.

    Args:
        valor: Fecha ISO 8601 tal como la manda la API.
    """
    momento = datetime.fromisoformat(valor)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(ZoneInfo(get_settings().store_timezone)).date()


async def ventas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a /ventas con el total vendido hoy (solo ventas pagadas).

    Recorre las ventas de 100 en 100, de la más reciente a la más antigua, y se
    detiene al llegar a una de un día anterior.

    Args:
        update: Mensaje recibido de Telegram.
        context: Contexto del bot (no se usa).
    """
    total = 0.0
    offset = 0
    # "Hoy" en la tienda, no en UTC
    today = datetime.now(ZoneInfo(get_settings().store_timezone)).date()

    try:
        # Con login activo, el bot se identifica con el token interno (solo lectura)
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8000", timeout=5, headers=internal_headers()
        ) as client:
            while True:
                response = await client.get(
                    "/api/sales",
                    params={"limit": 100, "offset": offset},
                )
                response.raise_for_status()
                sales = response.json()

                if not sales:
                    break

                for sale in sales:
                    if fecha_tienda(sale["created_at"]) == today and sale["status"] == "pagada":
                        total += float(sale["total"])

                if len(sales) < 100 or fecha_tienda(sales[-1]["created_at"]) < today:
                    break

                offset += 100
    except httpx.HTTPError:
        await update.message.reply_text("No se pudieron consultar las ventas.")
        return

    print("TELEGRAM: recibi /ventas", flush=True)
    await update.message.reply_text(f"Ventas de hoy: ${total:.2f}")
