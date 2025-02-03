from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..models import Upload, PlatformStatus, PostStatus, PlatformType
from .platforms.youtube import YouTubeService
from .platforms.instagram import InstagramService
from .platforms.tiktok import TikTokService
import asyncio
from datetime import datetime

class UploadManager:
    def __init__(self, db: Session):
        self.db = db
        self.youtube = YouTubeService()
        self.instagram = InstagramService()
        self.tiktok = TikTokService()

    async def process_upload(self, upload_id: str):
        """Process an upload for all configured platforms"""
        upload = self.db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            return
        
        upload.status = PostStatus.UPLOADING
        self.db.commit()
        
        try:
            tasks = []
            for platform_status in upload.platform_statuses:
                if platform_status.status != PostStatus.FAILED:
                    task = self._upload_to_platform(upload, platform_status)
                    tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Check if all platforms are complete
            all_complete = all(
                ps.status == PostStatus.COMPLETED
                for ps in upload.platform_statuses
            )
            
            upload.status = PostStatus.COMPLETED if all_complete else PostStatus.FAILED
            self.db.commit()
            
        except Exception as e:
            upload.status = PostStatus.FAILED
            upload.error = str(e)
            self.db.commit()

    async def _upload_to_platform(self, upload: Upload, platform_status: PlatformStatus):
        """Upload to a specific platform"""
        try:
            platform_status.status = PostStatus.UPLOADING
            self.db.commit()
            
            # Get platform-specific content
            content = upload.content.get(platform_status.platform.value, {})
            
            # Create progress callback
            def update_progress(progress: float):
                platform_status.progress = int(progress)
                self.db.commit()
            
            # Upload based on platform
            if platform_status.platform == PlatformType.YOUTUBE:
                await self.youtube.authenticate(platform_status.account)
                result = await self.youtube.upload_video(
                    video_path=upload.video_path,
                    title=content.get('title', ''),
                    description=content.get('description', ''),
                    tags=content.get('hashtags', []),
                    progress_callback=update_progress
                )
            
            elif platform_status.platform == PlatformType.INSTAGRAM:
                caption = f"{content.get('title', '')}\n\n{content.get('description', '')}\n\n{' '.join(content.get('hashtags', []))}"
                result = await self.instagram.upload_video(
                    video_path=upload.video_path,
                    caption=caption,
                    progress_callback=update_progress
                )
            
            elif platform_status.platform == PlatformType.TIKTOK:
                result = await self.tiktok.upload_video(
                    video_path=upload.video_path,
                    title=content.get('title', ''),
                    tags=content.get('hashtags', []),
                    progress_callback=update_progress
                )
            
            # Update status on success
            platform_status.status = PostStatus.COMPLETED
            platform_status.url = result.get('url')
            platform_status.progress = 100
            self.db.commit()
            
        except Exception as e:
            platform_status.status = PostStatus.FAILED
            platform_status.error = str(e)
            platform_status.progress = 0
            self.db.commit()
            raise

    async def process_queue(self):
        """Process all queued uploads"""
        queued_uploads = (
            self.db.query(Upload)
            .filter(Upload.status == PostStatus.QUEUED)
            .order_by(Upload.queue_position)
            .all()
        )
        
        for upload in queued_uploads:
            await self.process_upload(upload.id)

    async def process_scheduled(self):
        """Process scheduled uploads that are due"""
        now = datetime.utcnow()
        scheduled_uploads = (
            self.db.query(Upload)
            .filter(
                Upload.status == PostStatus.SCHEDULED,
                Upload.scheduled_time <= now
            )
            .all()
        )
        
        for upload in scheduled_uploads:
            await self.process_upload(upload.id)

    def clear_queue(self):
        """Clear all queued uploads"""
        self.db.query(Upload).filter(
            Upload.status == PostStatus.QUEUED
        ).update({
            "status": PostStatus.DRAFT,
            "queue_position": None
        })
        self.db.commit()

    def clear_schedule(self):
        """Clear all scheduled uploads"""
        self.db.query(Upload).filter(
            Upload.status == PostStatus.SCHEDULED
        ).update({
            "status": PostStatus.DRAFT,
            "scheduled_time": None
        })
        self.db.commit()
