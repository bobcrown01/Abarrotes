from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.routes.products import router as products_router
from app.routes.inventory import router as inventory_router
from app.routes.users import router as users_router

from app.database import engine

app = FastAPI(title="Abarrotes POS API")
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(users_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/health/db")
def health_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {"status": "ok", "database": "connected"}

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a la base de datos",
        )