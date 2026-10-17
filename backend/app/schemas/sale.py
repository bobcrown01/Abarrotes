from pydantic import BaseModel
from typing import Optional, List

class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    user_id: int

class SaleItemCreate(BaseModel):
    sale_id: int
    product_id: int
    qty: float
    price: float
    discount: float = 0

class PaymentCreate(BaseModel):
    sale_id: int
    method: str
    amount: float
    received: Optional[float] = None
    change: Optional[float] = None
    reference: Optional[str] = None
