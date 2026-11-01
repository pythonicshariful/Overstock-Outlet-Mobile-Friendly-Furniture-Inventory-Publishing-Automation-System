from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), index=True, nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)  # for showing discount e.g. "Retail $899, Overstock Price $399"
    description = Column(Text, nullable=True)
    category = Column(String(50), index=True, default="Living Room", nullable=False)
    condition = Column(String(50), default="Brand New", nullable=False)
    availability = Column(String(50), default="In Stock", nullable=False)
    status = Column(String(50), default="Draft", nullable=False)  # Draft, Ready, Published, Archived
    
    # Store dimensions/color if available
    dimensions = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    brand = Column(String(100), nullable=True)
    
    # Duplicate prevention hash
    content_hash = Column(String(64), index=True, nullable=True)
    
    date_added = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator = relationship("User", back_populates="products")
    
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="desc(ProductImage.is_primary), ProductImage.sort_order"
    )
    publish_logs = relationship(
        "PublishLog",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="desc(PublishLog.created_at)"
    )

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    file_size = Column(Integer, nullable=True)
    image_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="images")
