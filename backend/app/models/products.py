from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from app.database import Base
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    barcode = Column(String(50))
    sku = Column(String(50))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(Numeric(12,2), nullable=False)
    cost = Column(Numeric(12,2))
    unit = Column(String(20), default="pieza")
    is_active = Column(Boolean, default=True)
