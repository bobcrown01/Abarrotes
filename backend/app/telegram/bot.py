
from datetime import datetime

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    print("TELEGRAM: recibi /start", flush=True)
    await update.message.reply_text(
        "¡Hola! Soy el bot de tu sistema de abarrotes."
    )


async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "El sistema de abarrotes está funcionando."
    )


async def productos(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=5) as client:
            response = await client.get("/api/products")
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        await update.message.reply_text("No se pudieron consultar los productos.")
        return

    if not isinstance(data, list) or not all(
        isinstance(product, dict) and isinstance(product.get("is_active"), bool)
        for product in data
    ):
        await update.message.reply_text("La API devolvió una lista de productos inválida.")
        return

    active_count = sum(product["is_active"] for product in data)
    inactive_count = len(data) - active_count
    await update.message.reply_text(
        f"Productos dados de alta: {len(data)} "
        f"(activos: {active_count}, inactivos: {inactive_count})."
    )


def configurar_bot(token: str) -> Application:
    bot = Application.builder().token(token).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("estado", estado))
    bot.add_handler(CommandHandler("productos", productos))
    bot.add_handler(CommandHandler("ventas", ventas))

    return bot

async def ventas(update, context):
    total = 0.0
    offset = 0
    today = datetime.now().date()

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=5) as client:
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
                    created_at = datetime.fromisoformat(sale["created_at"])
                    if created_at.date() == today and sale["status"] == "pagada":
                        total += float(sale["total"])

                if len(sales) < 100 or datetime.fromisoformat(
                    sales[-1]["created_at"]
                ).date() < today:
                    break

                offset += 100
    except httpx.HTTPError:
        await update.message.reply_text("No se pudieron consultar las ventas.")
        return

    print("TELEGRAM: recibi /ventas", flush=True)
    await update.message.reply_text(f"Ventas de hoy: ${total:.2f}")
