from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Upload(Base):
    __tablename__ = "uploads"
    
    id = Column(String, primary_key=True)
    video_path = Column(String)
    analysis = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # pending, in_progress, completed, failed
    platform_statuses = relationship("PlatformStatus", back_populates="upload")

class PlatformStatus(Base):
    __tablename__ = "platform_statuses"
    
    id = Column(Integer, primary_key=True)
    upload_id = Column(String, ForeignKey("uploads.id"))
    platform = Column(String)  # youtube, instagram, tiktok
    account = Column(String)  # personal, charity
    status = Column(String)  # pending, uploading, completed, failed
    progress = Column(Integer)
    url = Column(String, nullable=True)
    error = Column(String, nullable=True)
    upload = relationship("Upload", back_populates="platform_statuses")
