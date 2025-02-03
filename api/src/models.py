from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import enum

class PostStatus(enum.Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"

class PlatformType(enum.Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"

class Upload(Base):
    __tablename__ = "uploads"
    
    id = Column(String, primary_key=True)
    video_path = Column(String)
    analysis = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_time = Column(DateTime, nullable=True)
    queue_position = Column(Integer, nullable=True)
    status = Column(Enum(PostStatus))
    content = Column(JSON)  # Generated content for each platform
    platform_statuses = relationship("PlatformStatus", back_populates="upload")
    error = Column(String, nullable=True)

class PlatformStatus(Base):
    __tablename__ = "platform_statuses"
    
    id = Column(Integer, primary_key=True)
    upload_id = Column(String, ForeignKey("uploads.id"))
    platform = Column(Enum(PlatformType))
    account = Column(String)  # personal, charity, etc.
    status = Column(Enum(PostStatus))
    progress = Column(Integer, default=0)
    url = Column(String, nullable=True)
    error = Column(String, nullable=True)
    content = Column(JSON)  # Platform-specific content
    upload = relationship("Upload", back_populates="platform_statuses")
