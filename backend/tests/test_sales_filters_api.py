"""Pruebas de los filtros y el resumen del historial de ventas."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.sale import Sale, SaleStatus


@pytest.fixture
def sales(db_session):
    """Tres ventas en días distintos, con estados distintos."""
    db_session.add_all(
        [
            Sale(
                id=1,
                folio="V-000001",
                status=SaleStatus.PAID,
                total=Decimal("100.50"),
                created_at=datetime(2026, 1, 10, 12),
            ),
            Sale(
                id=2,
                folio="V-000002",
                status=SaleStatus.PAID,
                total=Decimal("50"),
                created_at=datetime(2026, 1, 11, 12),
            ),
            Sale(
                id=3,
                folio="V-000003",
                status=SaleStatus.CANCELLED,
                total=Decimal("999"),
                created_at=datetime(2026, 1, 11, 13),
            ),
        ]
    )
    db_session.commit()


def ids(response):
    return [sale["id"] for sale in response.json()]


def test_sin_filtros_regresa_todas_las_recientes_primero(db_client, sales):
    assert ids(db_client.get("/api/sales")) == [3, 2, 1]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"status": "cancelada"}, [3]),
        ({"folio": "000002"}, [2]),
        ({"folio": "v-000001"}, [1]),  # Sin distinguir mayúsculas
        ({"folio": "%"}, []),  # No funciona como comodín
        ({"start": "2026-01-11T00:00:00"}, [3, 2]),
        ({"end": "2026-01-11T00:00:00"}, [1]),
        ({"start": "2026-01-11T00:00:00", "status": "pagada"}, [2]),
        ({"limit": 1}, [3]),
        ({"limit": 1, "offset": 2}, [1]),
    ],
)
def test_filtros(db_client, sales, params, expected):
    assert ids(db_client.get("/api/sales", params=params)) == expected


def test_fechas_con_zona_se_convierten_a_utc(db_client, sales):
    # Medianoche del 11 en México (UTC-6) son las 06:00 UTC: la venta de las 12:00 UTC entra
    response = db_client.get(
        "/api/sales",
        params={"start": "2026-01-11T00:00:00-06:00", "end": "2026-01-11T12:30:00-06:00"},
    )

    assert ids(response) == [3, 2]


def test_resumen_solo_cuenta_ventas_pagadas(db_client, sales):
    assert db_client.get("/api/sales/summary").json() == {"count": 2, "total": 150.5}


def test_resumen_respeta_el_rango(db_client, sales):
    response = db_client.get("/api/sales/summary", params={"start": "2026-01-11T00:00:00"})

    assert response.json() == {"count": 1, "total": 50}


def test_resumen_sin_ventas_da_cero(db_client):
    assert db_client.get("/api/sales/summary").json() == {"count": 0, "total": 0}


@pytest.mark.parametrize(
    "params",
    [
        {"status": "inventado"},
        {"start": "no-es-fecha"},
        {"start": "2026-01-12T00:00:00", "end": "2026-01-11T00:00:00"},
        {"limit": 101},
    ],
)
def test_filtros_invalidos_responden_422(db_client, params):
    assert db_client.get("/api/sales", params=params).status_code == 422
