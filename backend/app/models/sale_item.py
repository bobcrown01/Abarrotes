from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    qty = Column(Numeric(14,3), nullable=False)
    price = Column(Numeric(12,2), nullable=False)
    discount = Column(Numeric(12,2), default=0)
    subtotal = Column(Numeric(12,2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")
