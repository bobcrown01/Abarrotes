"""Fixtures compartidas: repositorios en memoria y cliente HTTP de prueba.

Las pruebas no necesitan PostgreSQL: el servicio recibe repositorios falsos
que cumplen los mismos protocolos que los reales.
"""

import os
from collections.abc import Iterator, Sequence
from decimal import Decimal

# Debe definirse antes de importar la app; create_engine no se conecta.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("APP_ENV", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.products import Category, Product
from app.models.role import Role
from app.models.user import User
from app.routes.dependencies import get_product_service
from app.services.product_service import ProductService
from app.utils.security import hash_password


class FakeCategoryRepository:
    def __init__(self, categories: list[Category]) -> None:
        self.categories = categories

    def list_all(self) -> Sequence[Category]:
        return sorted(self.categories, key=lambda c: c.name)

    def exists(self, category_id: int) -> bool:
        return any(c.id == category_id for c in self.categories)


class FakeProductRepository:
    def __init__(self) -> None:
        self.products: list[Product] = []

    def list_all(self) -> Sequence[Product]:
        return sorted(self.products, key=lambda p: p.id, reverse=True)

    def search(self, query: str, limit: int, offset: int) -> Sequence[Product]:
        q = query.lower()
        found = [
            p
            for p in self.products
            if any(q in (v or "").lower() for v in (p.name, p.barcode, p.sku))
        ]
        return found[offset : offset + limit]

    def get(self, product_id: int) -> Product | None:
        return next((p for p in self.products if p.id == product_id), None)

    def barcode_exists(self, barcode: str, exclude_id: int | None = None) -> bool:
        return any(p.barcode == barcode and p.id != exclude_id for p in self.products)

    def add(self, product: Product) -> Product:
        product.id = len(self.products) + 1
        self.products.append(product)
        return product

    def save(self, product: Product) -> Product:
        return product

    def filter(self, filters):  # Los filtros se prueban contra SQLite
        raise NotImplementedError


@pytest.fixture
def categories() -> FakeCategoryRepository:
    return FakeCategoryRepository(
        [Category(id=1, name="Abarrotes"), Category(id=2, name="Bebidas")]
    )


@pytest.fixture
def products() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def service(products: FakeProductRepository, categories: FakeCategoryRepository) -> ProductService:
    return ProductService(products, categories)


@pytest.fixture
def client(service: ProductService) -> Iterator[TestClient]:
    app.dependency_overrides[get_product_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------- Base de datos real (SQLite en memoria) ----------
# Prueba repositorios + servicios + rutas juntos. SQLite ignora FOR UPDATE;
# los bloqueos solo se ejercitan contra PostgreSQL.


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()

    session.add_all(
        [
            Category(id=1, name="Bebidas"),
            Role(id=1, name="cajero"),
            User(id=1, username="caja1", password_hash=hash_password("secreto123"), role_id=1),
            Product(id=1, name="Coca Cola 600ml", category_id=1, price=Decimal("18.50")),
            Product(id=2, name="Sabritas", category_id=1, price=Decimal("21.00")),
            Product(id=3, name="Descontinuado", category_id=1, price=Decimal("5"), is_active=False),
        ]
    )
    session.commit()

    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def db_client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "name": "Coca Cola 600ml",
        "barcode": "7501234567890",
        "sku": "COCA600",
        "category_id": 2,
        "price": 18.50,
        "cost": 12.00,
        "unit": "pieza",
        "is_active": True,
    }
