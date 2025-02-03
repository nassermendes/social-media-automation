from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import os

from ..database import get_db
from ..models import Upload, PlatformStatus, PostStatus, PlatformType
from ..services.video_analysis import VideoAnalysisService
from ..services.content_generation import ContentGenerationService

router = APIRouter()
video_service = VideoAnalysisService()
content_service = ContentGenerationService()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and analyze a video file"""
    try:
        # Generate unique ID and save file
        upload_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create upload record
        upload = Upload(
            id=upload_id,
            video_path=file_path,
            status=PostStatus.DRAFT
        )
        db.add(upload)
        db.commit()
        
        # Analyze video
        try:
            analysis = await video_service.analyze_video(file_path)
            upload.analysis = analysis
            db.commit()
            
            return {
                "upload_id": upload_id,
                "analysis": analysis
            }
        except Exception as e:
            upload.status = PostStatus.FAILED
            upload.error = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File upload failed: {str(e)}")

@router.post("/generate-content/{upload_id}")
async def generate_content(
    upload_id: str,
    platforms: List[PlatformType],
    db: Session = Depends(get_db)
):
    """Generate content for specified platforms"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    try:
        # Generate content using GPT
        content = await content_service.generate_content(
            upload.analysis,
            [p.value for p in platforms]
        )
        
        # Save generated content
        upload.content = content
        db.commit()
        
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")

@router.post("/schedule/{upload_id}")
async def schedule_post(
    upload_id: str,
    scheduled_time: Optional[datetime] = None,
    queue_position: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Schedule or queue a post"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    try:
        if scheduled_time:
            upload.status = PostStatus.SCHEDULED
            upload.scheduled_time = scheduled_time
            upload.queue_position = None
        elif queue_position is not None:
            upload.status = PostStatus.QUEUED
            upload.queue_position = queue_position
            upload.scheduled_time = None
        else:
            upload.status = PostStatus.UPLOADING
            # Trigger immediate upload process
        
        db.commit()
        return {"status": "success", "upload_id": upload_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")

@router.get("/status/{upload_id}")
async def get_status(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """Get current status of an upload"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return {
        "status": upload.status.value,
        "scheduled_time": upload.scheduled_time,
        "queue_position": upload.queue_position,
        "error": upload.error,
        "platforms": [
            {
                "platform": status.platform.value,
                "status": status.status.value,
                "progress": status.progress,
                "url": status.url,
                "error": status.error
            }
            for status in upload.platform_statuses
        ]
    }

@router.post("/queue/clear")
async def clear_queue(db: Session = Depends(get_db)):
    """Clear all queued posts"""
    try:
        db.query(Upload).filter(Upload.status == PostStatus.QUEUED).update(
            {"status": PostStatus.DRAFT, "queue_position": None}
        )
        db.commit()
        return {"status": "success", "message": "Queue cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear queue: {str(e)}")

@router.post("/schedule/clear")
async def clear_schedule(db: Session = Depends(get_db)):
    """Clear all scheduled posts"""
    try:
        db.query(Upload).filter(Upload.status == PostStatus.SCHEDULED).update(
            {"status": PostStatus.DRAFT, "scheduled_time": None}
        )
        db.commit()
        return {"status": "success", "message": "Schedule cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear schedule: {str(e)}")

@router.post("/post-now/{upload_id}")
async def post_now(
    upload_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Move a queued or scheduled post to immediate upload"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    try:
        upload.status = PostStatus.UPLOADING
        upload.scheduled_time = None
        upload.queue_position = None
        db.commit()
        
        # Trigger upload process in background
        # background_tasks.add_task(upload_service.process_upload, upload_id)
        
        return {"status": "success", "message": "Upload started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start upload: {str(e)}")
