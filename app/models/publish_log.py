from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class PublishLog(Base):
    __tablename__ = "publish_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    platform = Column(String(50), nullable=False)  # "facebook_page", "instagram", "marketplace"
    status = Column(String(50), nullable=False)    # "pending", "success", "failed", "assisted"
    external_id = Column(String(100), nullable=True) # Graph API post ID or container ID
    post_url = Column(String(500), nullable=True)    # Live URL to view post
    error_message = Column(Text, nullable=True)     # Detailed error if failed
    payload_summary = Column(Text, nullable=True)   # Summary of text/images sent
    retries = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="publish_logs")

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

