"""Pruebas unitarias de las reglas de negocio de productos."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.products import Product
from app.schemas.product import ProductCreate
from app.services.product_service import (
    CategoryNotFoundError,
    DuplicateBarcodeError,
    ProductService,
)


def test_create_product_saves_and_returns_id(service, products, valid_payload):
    product = service.create_product(ProductCreate(**valid_payload))

    assert product.id == 1
    assert product.price == Decimal("18.50")
    assert products.products == [product]


def test_create_product_rejects_unknown_category(service, valid_payload):
    with pytest.raises(CategoryNotFoundError):
        service.create_product(ProductCreate(**{**valid_payload, "category_id": 99}))


def test_create_product_rejects_duplicate_barcode(service, valid_payload):
    service.create_product(ProductCreate(**valid_payload))

    with pytest.raises(DuplicateBarcodeError):
        service.create_product(ProductCreate(**{**valid_payload, "name": "Otra"}))


def test_products_without_barcode_can_repeat(service, valid_payload):
    payload = {**valid_payload, "barcode": None}

    service.create_product(ProductCreate(**payload))
    service.create_product(ProductCreate(**payload))


def test_database_unique_violation_becomes_duplicate_error(categories, valid_payload):
    class RacingRepository:
        """Simula que otra alta guardó el mismo código entre la validación y el insert."""

        def barcode_exists(self, barcode: str) -> bool:
            return False

        def add(self, product: Product) -> Product:
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    service = ProductService(RacingRepository(), categories)  # type: ignore[arg-type]

    with pytest.raises(DuplicateBarcodeError):
        service.create_product(ProductCreate(**valid_payload))


def test_schema_strips_text_and_turns_blank_optional_fields_into_none(valid_payload):
    data = ProductCreate(**{**valid_payload, "name": "  Leche  ", "barcode": "  ", "sku": ""})

    assert data.name == "Leche"
    assert data.barcode is None
    assert data.sku is None
