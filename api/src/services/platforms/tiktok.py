import requests
from typing import Dict, Optional, List, Tuple
from ...config import get_settings
from moviepy.editor import VideoFileClip
import os
import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import json

settings = get_settings()
logger = logging.getLogger(__name__)

class TikTokService:
    def __init__(self):
        self.base_url = "https://open.tiktokapis.com/v2"
        self.app_key = settings.TIKTOK_APP_KEY
        self.app_secret = settings.TIKTOK_APP_SECRET
        self.credentials = {
            "personal": {
                "client_key": settings.TIKTOK_PERSONAL_CLIENT_KEY,
                "client_secret": settings.TIKTOK_PERSONAL_CLIENT_SECRET,
                "access_token": settings.TIKTOK_PERSONAL_ACCESS_TOKEN
            },
            "charity": {
                "client_key": settings.TIKTOK_CHARITY_CLIENT_KEY,
                "client_secret": settings.TIKTOK_CHARITY_CLIENT_SECRET,
                "access_token": settings.TIKTOK_CHARITY_ACCESS_TOKEN
            }
        }
        self.supported_formats = ['.mp4', '.mov']  # TikTok is more restrictive
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # TikTok specific settings
        self.privacy_options = ['public', 'private', 'friends']
        self.max_duration = 180  # 3 minutes
        self.max_file_size = 512 * 1024 * 1024  # 512MB
        self.allowed_aspect_ratios = [(9, 16), (1, 1), (16, 9)]  # Vertical, square, horizontal

    def _prepare_video_for_tiktok(self, video_path: str) -> Tuple[str, Dict]:
        """Prepare video for TikTok format and return metadata"""
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
        
        # Check if video meets TikTok requirements
        duration = clip.duration
        width, height = clip.size
        current_aspect_ratio = height / width
        file_size = os.path.getsize(video_path)
        
        temp_path = None
        modifications = []
        
        needs_modification = (
            duration > self.max_duration or
            file_size > self.max_file_size or
            not any(abs(current_aspect_ratio - (h/w)) < 0.1 for w, h in self.allowed_aspect_ratios)
        )
        
        if needs_modification:
            # Create temporary file for modified video
            temp_path = f"{os.path.splitext(video_path)[0]}_tiktok.mp4"
            
            # Adjust aspect ratio if needed
            if not any(abs(current_aspect_ratio - (h/w)) < 0.1 for w, h in self.allowed_aspect_ratios):
                # Default to 9:16 if aspect ratio is not standard
                target_ratio = 9/16
                if abs(current_aspect_ratio - (16/9)) < abs(current_aspect_ratio - (9/16)):
                    target_ratio = 16/9
                
                if current_aspect_ratio > target_ratio:
                    # Video is too tall
                    new_height = int(width * target_ratio)
                    y_center = height / 2
                    clip = clip.crop(y_center=(y_center), height=new_height)
                    modifications.append(f"Adjusted aspect ratio to {1/target_ratio}:1")
                else:
                    # Video is too wide
                    new_width = int(height / target_ratio)
                    x_center = width / 2
                    clip = clip.crop(x_center=(x_center), width=new_width)
                    modifications.append(f"Adjusted aspect ratio to {target_ratio}:1")
            
            # Trim to max duration if needed
            if duration > self.max_duration:
                clip = clip.subclip(0, self.max_duration)
                modifications.append(f"Trimmed to {self.max_duration} seconds")
            
            # Write the modified video with optimal settings for TikTok
            clip.write_videofile(
                temp_path,
                codec='libx264',
                audio_codec='aac',
                bitrate='6000k',
                audio_bitrate='128k',
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
                    audio_bitrate='96k',
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
            logger.error(f"TikTok API request failed: {str(e)}")
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code < 500:
                error_data = e.response.json()
                raise Exception(f"TikTok API error: {error_data.get('error_msg', str(e))}")
            raise

    async def upload_video(
        self,
        video_path: str,
        title: str,
        tags: list,
        account: str = "personal",
        privacy: str = "private",
        allow_comments: bool = True,
        allow_duets: bool = True,
        allow_stitch: bool = True,
        schedule_time: Optional[int] = None,
        progress_callback: Optional[callable] = None,
        additional_metadata: Optional[Dict] = None
    ) -> Dict:
        """Upload video to TikTok"""
        try:
            if account not in self.credentials:
                raise ValueError(f"Invalid account type: {account}")

            # Validate privacy setting
            if privacy not in self.privacy_options:
                raise ValueError(f"Invalid privacy setting. Must be one of: {', '.join(self.privacy_options)}")

            # Check file format
            file_ext = os.path.splitext(video_path)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}. Supported formats: {', '.join(self.supported_formats)}")

            # Prepare video for TikTok format
            tiktok_video_path, metadata = self._prepare_video_for_tiktok(video_path)
            logger.info(f"Video preparation metadata: {metadata}")
            
            # Get account credentials
            creds = self.credentials[account]
            
            # Step 1: Initialize upload
            init_response = await self._make_request(
                'post',
                f"{self.base_url}/video/upload/",
                headers={'Authorization': f'Bearer {creds["access_token"]}'}
            )
            upload_id = init_response['data']['upload_id']
            
            # Step 2: Upload video chunks
            chunk_size = 5 * 1024 * 1024  # 5MB chunks
            total_size = os.path.getsize(tiktok_video_path)
            chunks = (total_size + chunk_size - 1) // chunk_size
            
            with open(tiktok_video_path, 'rb') as file:
                for i in range(chunks):
                    chunk = file.read(chunk_size)
                    start = i * chunk_size
                    end = min(start + chunk_size - 1, total_size - 1)
                    
                    # Retry logic for chunk upload
                    retries = 0
                    while retries < self.max_retries:
                        try:
                            response = requests.put(
                                init_response['data']['upload_url'],
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
            
            # Step 3: Publish video
            publish_data = {
                'upload_id': upload_id,
                'title': title,
                'privacy_level': privacy.upper(),
                'disable_comments': not allow_comments,
                'disable_duet': not allow_duets,
                'disable_stitch': not allow_stitch
            }
            
            # Add schedule time if provided
            if schedule_time:
                publish_data['schedule_time'] = schedule_time
            
            # Add additional metadata from ChatGPT
            if additional_metadata:
                if 'branded_content' in additional_metadata:
                    publish_data['brand_content_info'] = additional_metadata['branded_content']
                if 'mentions' in additional_metadata:
                    publish_data['mentions'] = additional_metadata['mentions']
            
            result = await self._make_request(
                'post',
                f"{self.base_url}/video/publish/",
                headers={
                    'Authorization': f'Bearer {creds["access_token"]}',
                    'Content-Type': 'application/json'
                },
                json=publish_data
            )
            
            # Clean up temporary file if created
            if tiktok_video_path != video_path:
                os.remove(tiktok_video_path)
            
            final_result = {
                'video_id': result['data']['video_id'],
                'url': f"https://tiktok.com/@{result['data']['creator_username']}/video/{result['data']['video_id']}",
                'metadata': metadata
            }
            
            logger.info(f"Successfully uploaded video: {final_result}")
            return final_result
            
        except Exception as e:
            # Clean up temporary file if created and error occurred
            if tiktok_video_path != video_path and os.path.exists(tiktok_video_path):
                os.remove(tiktok_video_path)
            logger.error(f"TikTok upload failed: {str(e)}")
            raise Exception(f"TikTok upload failed: {str(e)}")

    async def get_upload_status(self, video_id: str, account: str = "personal") -> Dict:
        """Get the status of an uploaded video"""
        if account not in self.credentials:
            raise ValueError(f"Invalid account type: {account}")
            
        creds = self.credentials[account]
        url = f"{self.base_url}/video/query/"
        
        response = await self._make_request(
            'get',
            url,
            headers={'Authorization': f'Bearer {creds["access_token"]}'},
            params={'video_id': video_id}
        )
        
        return response['data']
