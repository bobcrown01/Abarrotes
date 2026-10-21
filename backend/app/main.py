"""Punto de entrada de la API del POS de abarrotes."""

import logging
import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.database import engine
from app.routes.inventory import router as inventory_router
from app.routes.products import router as products_router
from app.routes.sales import router as sales_router
from app.routes.users import router as users_router

from contextlib import asynccontextmanager
from app.telegram.bot import configurar_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN")

    bot = configurar_bot(token)
    await bot.initialize()
    await bot.start()

    # Inicia la recepción de mensajes de Telegram
    await bot.updater.start_polling()

    app.state.telegram_bot = bot

    try:
        yield
    finally:
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Abarrotes POS API",
    lifespan=lifespan,  # Esta línea activa la inicialización de Telegram
    # La documentación interactiva solo se expone fuera de producción
    docs_url=None if settings.app_env == "production" else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.app_env == "production" else "/api/openapi.json",
)
register_exception_handlers(app)

app.include_router(products_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(sales_router, prefix="/api")

@app.get("/api/health")
def health() -> dict[str, str]:
    """Indica que el proceso está vivo (lo usa el healthcheck de Docker)."""
    return {"status": "ok"}


@app.get("/api/health/db")
def health_db() -> dict[str, str]:
    """Verifica la conexión con la base de datos.

    Raises:
        HTTPException: 503 si la base no responde.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Healthcheck de base de datos falló: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a la base de datos",
        ) from exc

    return {"status": "ok", "database": "connected"}
