from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.products import Product
from app.schemas.inventory import InventoryMovementCreate

router = APIRouter()

@router.post("/inventory/movements")
def create_inventory_movement(data: InventoryMovementCreate, db: Session = Depends(get_db)):

    # Validar producto
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Obtener inventario actual
    inventory = db.query(Inventory).filter(Inventory.product_id == data.product_id).first()

    if not inventory:
        inventory = Inventory(product_id=data.product_id, quantity=Decimal("0"))
        db.add(inventory)

    # Calcular nuevo inventario
    if data.type == "entrada":
        inventory.quantity += data.quantity

    elif data.type == "salida":
        if inventory.quantity < data.quantity:
            raise HTTPException(status_code=400, detail="Inventario insuficiente")
        inventory.quantity -= data.quantity

    elif data.type == "ajuste":
        inventory.quantity = data.quantity

    else:
        raise HTTPException(status_code=400, detail="Tipo de movimiento inválido")

    # Registrar movimiento
    movement = InventoryMovement(
        product_id=data.product_id,
        type=data.type,
        quantity=data.quantity,
        reason=data.reason,
        user_id=data.user_id
    )

    db.add(movement)
    db.commit()
    db.refresh(movement)

    return {
        "status": "success",
        "message": "Movimiento registrado",
        "movement_id": movement.id,
        "new_quantity": float(inventory.quantity)
    }

@router.get("/inventory")
def get_inventory(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    category_id: int | None = None,
    in_stock: bool | None = None
):
    query = db.query(Inventory).join(Product)

    # Filtro por categoría
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Filtro por productos con stock > 0
    if in_stock is True:
        query = query.filter(Inventory.quantity > 0)

    # Filtro por productos sin stock
    if in_stock is False:
        query = query.filter(Inventory.quantity <= 0)

    results = query.limit(limit).offset(offset).all()

    return [
        {
            "product_id": inv.product_id,
            "product_name": inv.product.name,
            "quantity": float(inv.quantity),
            "min_stock": float(inv.min_stock),
            "max_stock": float(inv.max_stock) if inv.max_stock else None,
            "unit": inv.product.unit,
            "is_active": inv.product.is_active
        }
        for inv in results
    ]

@router.get("/inventory/{product_id}")
def get_inventory_by_product(product_id: int, db: Session = Depends(get_db)):

    inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()

    if not inv:
        raise HTTPException(404, "Inventario no encontrado para este producto")

    return {
        "product_id": inv.product_id,
        "product_name": inv.product.name,
        "quantity": float(inv.quantity),
        "min_stock": float(inv.min_stock),
        "max_stock": float(inv.max_stock) if inv.max_stock else None,
        "unit": inv.product.unit,
        "is_active": inv.product.is_active
    }

@router.get("/inventory/movements")
def get_inventory_movements(
    db: Session = Depends(get_db),
    product_id: int | None = None,
    type: str | None = None,  # entrada / salida / ajuste
    user_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0
):
    query = db.query(InventoryMovement).join(Product)

    if product_id:
        query = query.filter(InventoryMovement.product_id == product_id)

    if type:
        query = query.filter(InventoryMovement.type == type)

    if user_id:
        query = query.filter(InventoryMovement.user_id == user_id)

    if start_date:
        query = query.filter(InventoryMovement.created_at >= start_date)

    if end_date:
        query = query.filter(InventoryMovement.created_at <= end_date)

    movements = query.order_by(InventoryMovement.id.desc()).limit(limit).offset(offset).all()

    return [
        {
            "movement_id": m.id,
            "product_id": m.product_id,
            "product_name": m.product.name,
            "type": m.type,
            "quantity": float(m.quantity),
            "reason": m.reason,
            "created_at": m.created_at,
            "user_id": m.user_id
        }
        for m in movements
    ]

@router.get("/inventory/{product_id}/movements")
def get_movements_by_product(product_id: int, db: Session = Depends(get_db)):

    movements = db.query(InventoryMovement).filter(
        InventoryMovement.product_id == product_id
    ).order_by(InventoryMovement.id.desc()).all()

    return [
        {
            "movement_id": m.id,
            "type": m.type,
            "quantity": float(m.quantity),
            "reason": m.reason,
            "created_at": m.created_at,
            "user_id": m.user_id
        }
        for m in movements
    ]
