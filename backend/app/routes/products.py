from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.products import Product
from app.models.inventory import Inventory
from app.schemas.product import ProductCreate
from app.schemas.product import ProductOut

router = APIRouter()

@router.post("/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):

    # Validar que la categoría exista
    category_exists = db.execute(
        text("SELECT id FROM categories WHERE id = :id"),
        {"id": product.category_id}
    ).fetchone()

    if not category_exists:
        raise HTTPException(status_code=400, detail="La categoría no existe")

    new_product = Product(
        name=product.name,
        barcode=product.barcode,
        sku=product.sku,
        category_id=product.category_id,
        price=product.price,
        cost=product.cost,
        unit=product.unit,
        is_active=product.is_active
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return {
        "status": "success",
        "message": "Producto creado correctamente",
        "product_id": new_product.id
    }

@router.get("/products", response_model=list[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products

@router.get("/products/search", response_model=list[ProductOut])
def search_products(
    q: str,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Busca productos por nombre, barcode o SKU.
    Soporta coincidencias parciales.
    """

    query = db.query(Product).filter(
        or_(
            Product.name.ilike(f"%{q}%"),
            Product.barcode.ilike(f"%{q}%"),
            Product.sku.ilike(f"%{q}%")
        )
    ).limit(limit).offset(offset)

    return query.all()

@router.get("/products/filter", response_model=list[ProductOut])
def filter_products(
    db: Session = Depends(get_db),
    search: str | None = None,
    category_id: int | None = None,
    active: bool | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock: bool | None = None,
    limit: int = 50,
    offset: int = 0
):
    query = db.query(Product)

    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.barcode.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%")
            )
        )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if active is not None:
        query = query.filter(Product.is_active == active)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if in_stock is not None:
        query = query.join(Inventory, Inventory.product_id == Product.id)
        if in_stock:
            query = query.filter(Inventory.quantity > 0)
        else:
            query = query.filter(Inventory.quantity <= 0)

    return query.limit(limit).offset(offset).all()
