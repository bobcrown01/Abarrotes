"""Pruebas de los avisos por Telegram y de la fecha de la tienda en /ventas."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.core.config import get_settings
from app.main import app
from app.services.cash_service import CashSummary
from app.services.inventory_service import StockView
from app.telegram.bot import fecha_tienda
from app.telegram.notifications import MAX_LISTED_PRODUCTS, cash_report_text


def stock(name, quantity, minimum=0):
    return StockView(1, name, Decimal(quantity), Decimal(minimum), None, "pieza", True)


def summary(counted, expected="118.50", notes=None):
    return CashSummary(
        id=7,
        opened_by=1,
        opened_at=datetime(2026, 1, 1),
        opening_amount=Decimal("100"),
        counted_amount=Decimal(counted),
        expected_cash=Decimal(expected),
        difference=Decimal(counted) - Decimal(expected),
        sales_total=Decimal("1234.5"),
        sales_count=3,
        notes=notes,
    )


def test_mensaje_del_corte_con_faltante_y_por_surtir():
    text = cash_report_text(summary("110", notes="Pago a proveedor"), "caja1", [stock("Coca", "0")])

    assert text.splitlines() == [
        "Corte de caja #7",
        "Hizo el corte: caja1",
        "Ventas: 3 · $1,234.50",
        "Efectivo esperado: $118.50",
        "Efectivo contado: $110.00",
        "Resultado: Faltante $8.50",
        "Notas: Pago a proveedor",
        "",
        "Por surtir (1):",
        "- Coca: quedan 0",
    ]


def test_mensaje_cuando_cuadra_y_sin_faltantes():
    text = cash_report_text(summary("118.50"), "caja1", [])

    assert "Resultado: Cuadra" in text
    assert "Por surtir" not in text


def test_mensaje_recorta_listas_largas():
    many = [stock(f"P{i}", "1") for i in range(MAX_LISTED_PRODUCTS + 5)]

    text = cash_report_text(summary("118.50"), "caja1", many)

    assert f"Por surtir ({MAX_LISTED_PRODUCTS + 5}):" in text
    assert text.endswith("... y 5 más")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-01-11T05:59:00", date(2026, 1, 10)),  # 23:59 en México: aún es el día 10
        ("2026-01-11T06:00:00", date(2026, 1, 11)),
        ("2026-01-11T00:30:00+00:00", date(2026, 1, 10)),
    ],
)
def test_fecha_tienda_usa_la_zona_de_mexico(value, expected):
    assert fecha_tienda(value) == expected


class FakeBot:
    """Imita la parte del bot de python-telegram-bot que usan los avisos."""

    def __init__(self):
        self.sent = []
        self.bot = self

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


@pytest.fixture
def fake_bot(monkeypatch):
    bot = FakeBot()
    # monkeypatch quita el bot falso al terminar la prueba
    monkeypatch.setattr(app.state, "telegram_bot", bot, raising=False)
    return bot


def test_el_corte_avisa_por_telegram(db_client, fake_bot, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_chat_id", 12345)
    db_client.put("/api/inventory/1/min-stock", json={"min_stock": 5})

    assert db_client.post("/api/cash/close", json={"counted_amount": 100}).status_code == 200

    [(chat_id, text)] = fake_bot.sent
    assert chat_id == 12345
    assert "Resultado: Cuadra" in text
    assert "- Coca Cola 600ml: quedan 0" in text


def test_sin_chat_configurado_no_avisa(db_client, fake_bot, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_chat_id", None)

    db_client.post("/api/cash/close", json={"counted_amount": 100})

    assert fake_bot.sent == []
