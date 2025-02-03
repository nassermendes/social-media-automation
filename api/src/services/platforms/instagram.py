import requests
import json
from typing import Dict, Optional, List, Tuple
from ...config import get_settings
from moviepy.editor import VideoFileClip
import os
import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
logger = logging.getLogger(__name__)

class InstagramService:
    def __init__(self):
        self.base_url = "https://graph.instagram.com/v18.0"
        self.credentials = {
            "personal": {
                "access_token": settings.INSTAGRAM_PERSONAL_ACCESS_TOKEN,
                "user_id": settings.INSTAGRAM_PERSONAL_USER_ID
            },
            "charity": {
                "access_token": settings.INSTAGRAM_CHARITY_ACCESS_TOKEN,
                "user_id": settings.INSTAGRAM_CHARITY_USER_ID
            }
        }
        self.supported_formats = ['.mp4', '.mov']  # Instagram is restrictive
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Instagram specific settings
        self.max_duration = 90  # 90 seconds for Reels
        self.max_file_size = 250 * 1024 * 1024  # 250MB
        self.allowed_aspect_ratios = [(9, 16)]  # Only vertical for Reels
        self.min_width = 720
        self.max_width = 1080
        self.min_height = 1280
        self.max_height = 1920

    def _prepare_video_for_reels(self, video_path: str) -> Tuple[str, Dict]:
        """Prepare video for Instagram Reels format and return metadata"""
        clip = VideoFileClip(video_path)
        
        # Extract metadata
        metadata = {
            'original_duration': clip.duration,
            'original_size': (clip.size[0], clip.size[1]),
            'original_fps': clip.fps,
            'format': os.path.splitext(video_path)[1],
            'file_size': os.path.getsize(video_path),
            'audio_present': clip.audio is not None
        }
        
        # Check if video meets Reels requirements
        duration = clip.duration
        width, height = clip.size
        current_aspect_ratio = height / width
        file_size = os.path.getsize(video_path)
        
        temp_path = None
        modifications = []
        target_ratio = 9/16
        
        needs_modification = (
            duration > self.max_duration or
            file_size > self.max_file_size or
            abs(current_aspect_ratio - target_ratio) > 0.1 or
            width < self.min_width or width > self.max_width or
            height < self.min_height or height > self.max_height
        )
        
        if needs_modification:
            # Create temporary file for modified video
            temp_path = f"{os.path.splitext(video_path)[0]}_reel.mp4"
            
            # Adjust aspect ratio to 9:16
            if abs(current_aspect_ratio - target_ratio) > 0.1:
                if current_aspect_ratio < target_ratio:
                    # Video is too wide
                    new_width = int(height / target_ratio)
                    x_center = width / 2
                    clip = clip.crop(x_center=(x_center), width=new_width)
                    modifications.append(f"Cropped width to {new_width}px for 9:16 ratio")
                else:
                    # Video is too tall
                    new_height = int(width * target_ratio)
                    y_center = height / 2
                    clip = clip.crop(y_center=(y_center), height=new_height)
                    modifications.append(f"Cropped height to {new_height}px for 9:16 ratio")
            
            # Resize if dimensions are outside allowed range
            current_width, current_height = clip.size
            if (current_width < self.min_width or current_width > self.max_width or
                current_height < self.min_height or current_height > self.max_height):
                # Calculate target dimensions maintaining aspect ratio
                if current_width < self.min_width:
                    scale = self.min_width / current_width
                elif current_width > self.max_width:
                    scale = self.max_width / current_width
                else:
                    scale = 1
                
                new_width = int(current_width * scale)
                new_height = int(current_height * scale)
                
                # Ensure height is also within bounds
                if new_height > self.max_height:
                    scale = self.max_height / new_height
                    new_width = int(new_width * scale)
                    new_height = int(new_height * scale)
                elif new_height < self.min_height:
                    scale = self.min_height / new_height
                    new_width = int(new_width * scale)
                    new_height = int(new_height * scale)
                
                clip = clip.resize((new_width, new_height))
                modifications.append(f"Resized to {new_width}x{new_height}")
            
            # Trim to max duration if needed
            if duration > self.max_duration:
                clip = clip.subclip(0, self.max_duration)
                modifications.append(f"Trimmed to {self.max_duration} seconds")
            
            # Write the modified video with optimal settings for Instagram
            clip.write_videofile(
                temp_path,
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',  # High quality for Instagram
                audio_bitrate='192k',
                fps=30
            )
            
            # Check final file size
            if os.path.getsize(temp_path) > self.max_file_size:
                # If still too large, reduce bitrate and try again
                clip.write_videofile(
                    temp_path,
                    codec='libx264',
                    audio_codec='aac',
                    bitrate='4000k',
                    audio_bitrate='128k',
                    fps=30
                )
                modifications.append("Reduced quality to meet file size requirements")
            
            clip.close()
            
            # Update metadata with modifications
            metadata.update({
                'modified_duration': min(duration, self.max_duration),
                'modified_size': clip.size,
                'modifications': modifications,
                'temp_path': temp_path
            })
            
            return temp_path, metadata
        
        clip.close()
        return video_path, metadata

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """Make HTTP request with retry logic"""
        try:
            response = getattr(requests, method)(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Instagram API request failed: {str(e)}")
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code < 500:
                error_data = e.response.json()
                raise Exception(f"Instagram API error: {error_data.get('error', {}).get('message', str(e))}")
            raise

    async def upload_video(
        self,
        video_path: str,
        caption: str,
        account: str = "personal",
        share_to_feed: bool = True,
        location: Optional[Dict] = None,
        mentions: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
        additional_metadata: Optional[Dict] = None
    ) -> Dict:
        """Upload video to Instagram as Reel"""
        try:
            if account not in self.credentials:
                raise ValueError(f"Invalid account type: {account}")

            # Check file format
            file_ext = os.path.splitext(video_path)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}. Supported formats: {', '.join(self.supported_formats)}")

            # Prepare video for Reels format
            reels_video_path, metadata = self._prepare_video_for_reels(video_path)
            logger.info(f"Video preparation metadata: {metadata}")
            
            # Get account credentials
            creds = self.credentials[account]
            
            # Step 1: Create container
            container_response = await self._make_request(
                'post',
                f"{self.base_url}/{creds['user_id']}/media",
                params={
                    'access_token': creds['access_token'],
                    'media_type': 'REELS',
                    'video_url': reels_video_path,
                    'caption': caption,
                    'share_to_feed': share_to_feed
                }
            )
            
            creation_id = container_response['id']
            
            # Step 2: Upload video chunks
            chunk_size = 5 * 1024 * 1024  # 5MB chunks
            total_size = os.path.getsize(reels_video_path)
            chunks = (total_size + chunk_size - 1) // chunk_size
            
            with open(reels_video_path, 'rb') as file:
                for i in range(chunks):
                    chunk = file.read(chunk_size)
                    start = i * chunk_size
                    end = min(start + chunk_size - 1, total_size - 1)
                    
                    # Retry logic for chunk upload
                    retries = 0
                    while retries < self.max_retries:
                        try:
                            response = requests.post(
                                container_response['upload_url'],
                                headers={
                                    'Content-Range': f'bytes {start}-{end}/{total_size}',
                                    'Content-Type': 'video/mp4'
                                },
                                data=chunk
                            )
                            response.raise_for_status()
                            break
                        except Exception as e:
                            retries += 1
                            if retries == self.max_retries:
                                raise
                            logger.warning(f"Chunk upload failed, retrying ({retries}/{self.max_retries})")
                            time.sleep(self.retry_delay)
                    
                    if progress_callback:
                        progress = (i + 1) / chunks * 100
                        progress_callback(progress)
            
            # Step 3: Finalize upload with additional metadata
            publish_data = {
                'creation_id': creation_id,
                'share_to_feed': share_to_feed
            }
            
            if location:
                publish_data['location'] = location
            
            if mentions:
                publish_data['user_tags'] = mentions
            
            # Add additional metadata from ChatGPT
            if additional_metadata:
                if 'branded_content' in additional_metadata:
                    publish_data['branded_content_partner_id'] = additional_metadata['branded_content']
                if 'advanced_settings' in additional_metadata:
                    publish_data.update(additional_metadata['advanced_settings'])
            
            result = await self._make_request(
                'post',
                f"{self.base_url}/{creds['user_id']}/media_publish",
                params={
                    'access_token': creds['access_token'],
                    'creation_id': creation_id
                }
            )
            
            # Clean up temporary file if created
            if reels_video_path != video_path:
                os.remove(reels_video_path)
            
            final_result = {
                'media_id': result['id'],
                'url': f"https://instagram.com/reel/{result['id']}",
                'metadata': metadata
            }
            
            logger.info(f"Successfully uploaded video: {final_result}")
            return final_result
            
        except Exception as e:
            # Clean up temporary file if created and error occurred
            if reels_video_path != video_path and os.path.exists(reels_video_path):
                os.remove(reels_video_path)
            logger.error(f"Instagram upload failed: {str(e)}")
            raise Exception(f"Instagram upload failed: {str(e)}")

    async def get_upload_status(self, media_id: str, account: str = "personal") -> Dict:
        """Get the status of an uploaded media"""
        if account not in self.credentials:
            raise ValueError(f"Invalid account type: {account}")
            
        creds = self.credentials[account]
        
        response = await self._make_request(
            'get',
            f"{self.base_url}/{media_id}",
            params={
                'access_token': creds['access_token'],
                'fields': 'id,media_type,media_url,thumbnail_url,permalink,timestamp,caption'
            }
        )
        
        return response
