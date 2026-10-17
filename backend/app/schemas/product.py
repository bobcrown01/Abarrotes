from pydantic import BaseModel
from typing import Optional

class ProductCreate(BaseModel):
    name: str
    barcode: Optional[str] = None
    sku: Optional[str] = None
    category_id: int
    price: float
    cost: Optional[float] = None
    unit: Optional[str] = "pieza"
    is_active: Optional[bool] = True

class ProductOut(BaseModel):
    id: int
    name: str
    barcode: Optional[str]
    sku: Optional[str]
    category_id: int
    price: float
    cost: Optional[float]
    unit: Optional[str]
    is_active: bool