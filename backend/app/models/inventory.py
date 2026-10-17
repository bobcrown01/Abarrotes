from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(14,3), default=0)
    min_stock = Column(Numeric(14,3), default=0)
    max_stock = Column(Numeric(14,3))

    product = relationship("Product")
