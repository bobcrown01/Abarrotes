"""Pruebas del reporte de ventas."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.products import Product
from app.models.sale import Sale, SaleStatus
from app.models.sale_item import SaleItem
from app.models.user import User
from app.services.auth_service import login_throttle
from app.utils.security import hash_password


@pytest.fixture
def sales(db_session):
    """Ventas de prueba: Coca Cola con costo ($12), Sabritas sin costo.

    - 10 ene: 2 Coca ($37) + 1 Sabritas ($21) = $58, pagada
    - 11 ene: 1 Coca ($18.50), pagada
    - 11 ene: 5 Sabritas ($105), cancelada: no debe contar
    """
    db_session.get(Product, 1).cost = Decimal("12")
    sales = [
        (1, SaleStatus.PAID, "58", datetime(2026, 1, 10)),
        (2, SaleStatus.PAID, "18.5", datetime(2026, 1, 11)),
        (3, SaleStatus.CANCELLED, "105", datetime(2026, 1, 11)),
    ]
    items = [
        (1, 1, 2, "18.5", "37"),
        (1, 2, 1, "21", "21"),
        (2, 1, 1, "18.5", "18.5"),
        (3, 2, 5, "21", "105"),
    ]
    for sale_id, status, total, created_at in sales:
        db_session.add(Sale(id=sale_id, status=status, total=Decimal(total), created_at=created_at))
    for sale_id, product_id, qty, price, subtotal in items:
        db_session.add(
            SaleItem(
                sale_id=sale_id,
                product_id=product_id,
                qty=qty,
                price=Decimal(price),
                subtotal=Decimal(subtotal),
            )
        )
    db_session.commit()


def test_resumen_del_periodo(db_client, sales):
    report = db_client.get("/api/reports/sales").json()

    assert report["sales_count"] == 2
    assert report["sales_total"] == 76.5
    assert report["average_ticket"] == 38.25
    # Coca: vendió $55.50 con costo 3 × $12 = $36; Sabritas no tiene costo
    assert report["profit"] == 19.5
    assert report["revenue_without_cost"] == 21


def test_mas_vendidos_por_importe_sin_canceladas(db_client, sales):
    top = db_client.get("/api/reports/sales").json()["top_products"]

    assert top == [
        {"product_id": 1, "name": "Coca Cola 600ml", "quantity": 3, "total": 55.5},
        {"product_id": 2, "name": "Sabritas", "quantity": 1, "total": 21},
    ]


def test_sin_movimiento_solo_productos_activos(db_client, sales):
    params = {"start": "2026-01-11T00:00:00"}
    report = db_client.get("/api/reports/sales", params=params).json()

    # El 11 solo se vendió Coca; "Descontinuado" está inactivo y no aparece
    assert report["idle_products"] == [{"product_id": 2, "name": "Sabritas"}]
    assert report["idle_total"] == 1
    assert report["sales_total"] == 18.5


def test_periodo_sin_ventas_da_ceros(db_client):
    report = db_client.get("/api/reports/sales").json()

    assert report["sales_count"] == 0
    assert report["average_ticket"] == 0
    assert report["profit"] == 0
    assert report["top_products"] == []
    assert report["idle_total"] == 2


def test_rango_invertido_responde_422(db_client):
    params = {"start": "2026-01-12T00:00:00", "end": "2026-01-11T00:00:00"}

    assert db_client.get("/api/reports/sales", params=params).status_code == 422


def test_cajero_no_ve_reportes(anon_client, db_session):
    db_session.add(User(id=3, username="caja2", password_hash=hash_password("1234"), role_id=1))
    db_session.commit()
    login_throttle.reset("caja2")
    anon_client.post("/api/auth/login", json={"username": "caja2", "password": "1234"})

    assert anon_client.get("/api/reports/sales").status_code == 403
