from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import os
import pickle
from typing import Dict, Optional, List, Tuple
from ...config import get_settings
from moviepy.editor import VideoFileClip
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import json
import time

settings = get_settings()
logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.credentials = None
        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
        self.token_files = {
            "personal": "token_personal.pickle",
            "charity": "token_charity.pickle"
        }
        self.supported_formats = ['.mp4', '.mov', '.avi', '.mkv']
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.category_map = {
            'gaming': '20',
            'education': '27',
            'entertainment': '24',
            'howto': '26',
            'music': '10',
            'news': '25',
            'nonprofit': '29',
            'people': '22',
            'sports': '17',
            'tech': '28',
        }

    async def authenticate(self, account: str = "personal") -> None:
        """Authenticate with YouTube"""
        if account not in self.token_files:
            raise ValueError(f"Invalid account type: {account}")
            
        token_file = self.token_files[account]
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.credentials = pickle.load(token)

        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secret.json", self.scopes)
                self.credentials = flow.run_local_server(port=0)

            with open(token_file, 'wb') as token:
                pickle.dump(self.credentials, token)

    def _prepare_video_for_shorts(self, video_path: str) -> Tuple[str, Dict]:
        """Prepare video for YouTube Shorts format and return metadata"""
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
        
        # Check if video meets Shorts requirements
        max_duration = 60  # Shorts max duration is 60 seconds
        required_aspect_ratio = 9/16  # Vertical format
        min_width = 1080  # Minimum width for good quality
        
        duration = clip.duration
        width, height = clip.size
        current_aspect_ratio = height / width
        
        temp_path = None
        modifications = []
        
        if duration > max_duration or abs(current_aspect_ratio - required_aspect_ratio) > 0.1 or width < min_width:
            # Create temporary file for modified video
            temp_path = f"{os.path.splitext(video_path)[0]}_shorts.mp4"
            
            # Crop or pad video to achieve 9:16 aspect ratio if needed
            if abs(current_aspect_ratio - required_aspect_ratio) > 0.1:
                if current_aspect_ratio < required_aspect_ratio:
                    # Video is too wide, need to crop width
                    new_width = int(height / required_aspect_ratio)
                    x_center = width / 2
                    clip = clip.crop(x_center=(x_center), width=new_width)
                    modifications.append(f"Cropped width to {new_width}px")
                else:
                    # Video is too tall, need to crop height
                    new_height = int(width * required_aspect_ratio)
                    y_center = height / 2
                    clip = clip.crop(y_center=(y_center), height=new_height)
                    modifications.append(f"Cropped height to {new_height}px")
            
            # Resize if width is too small
            if width < min_width:
                scale_factor = min_width / width
                new_width = min_width
                new_height = int(height * scale_factor)
                clip = clip.resize((new_width, new_height))
                modifications.append(f"Resized to {new_width}x{new_height}")
            
            # Trim to 60 seconds if needed
            if duration > max_duration:
                clip = clip.subclip(0, max_duration)
                modifications.append(f"Trimmed to {max_duration} seconds")
            
            # Write the modified video with optimal settings
            clip.write_videofile(
                temp_path,
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',  # Higher bitrate for YouTube
                audio_bitrate='192k',
                fps=30
            )
            clip.close()
            
            # Update metadata with modifications
            metadata.update({
                'modified_duration': min(duration, max_duration),
                'modified_size': clip.size,
                'modifications': modifications,
                'temp_path': temp_path
            })
            
            return temp_path, metadata
        
        clip.close()
        return video_path, metadata

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_api_request(self, request) -> Dict:
        """Make YouTube API request with retry logic"""
        try:
            return request.execute()
        except HttpError as e:
            logger.error(f"YouTube API request failed: {str(e)}")
            if e.resp.status in [500, 502, 503, 504]:  # Retry on server errors
                raise
            else:
                error_details = json.loads(e.content.decode())
                raise Exception(f"YouTube API error: {error_details['error']['message']}")

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        account: str = "personal",
        privacy_status: str = "private",
        category: str = "entertainment",
        language: str = "en",
        made_for_kids: bool = False,
        notify_subscribers: bool = True,
        progress_callback: Optional[callable] = None,
        additional_metadata: Optional[Dict] = None
    ) -> Dict:
        """Upload video to YouTube as Shorts"""
        try:
            # Check file format
            file_ext = os.path.splitext(video_path)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}. Supported formats: {', '.join(self.supported_formats)}")

            # Prepare video for Shorts format
            shorts_video_path, metadata = self._prepare_video_for_shorts(video_path)
            logger.info(f"Video preparation metadata: {metadata}")
            
            youtube = build(
                self.api_service_name,
                self.api_version,
                credentials=self.credentials
            )

            # Add #Shorts hashtag to title and description if not present
            if "#Shorts" not in title:
                title = f"{title} #Shorts"
            if "#Shorts" not in description:
                description = f"{description}\n\n#Shorts"
            if "Shorts" not in tags:
                tags.append("Shorts")

            # Get category ID
            category_id = self.category_map.get(category.lower(), '22')  # Default to People & Blogs

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': category_id,
                    'defaultLanguage': language,
                    'defaultAudioLanguage': language
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': made_for_kids,
                    'shortForm': True,  # Mark as Shorts
                    'notifySubscribers': notify_subscribers
                }
            }

            # Add any additional metadata from ChatGPT
            if additional_metadata:
                if 'localizations' in additional_metadata:
                    body['localizations'] = additional_metadata['localizations']
                if 'thumbnail' in additional_metadata:
                    body['snippet']['thumbnails'] = additional_metadata['thumbnail']

            insert_request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=MediaFileUpload(
                    shorts_video_path,
                    chunksize=1024*1024,
                    resumable=True
                )
            )

            response = None
            retries = 0
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if status and progress_callback:
                        progress_callback(status.progress() * 100)
                except HttpError as e:
                    if retries >= self.max_retries:
                        raise
                    retries += 1
                    logger.warning(f"Upload chunk failed, retrying ({retries}/{self.max_retries})")
                    time.sleep(self.retry_delay)

            # Clean up temporary file if created
            if shorts_video_path != video_path:
                os.remove(shorts_video_path)

            result = {
                'video_id': response['id'],
                'url': f"https://youtube.com/shorts/{response['id']}",
                'metadata': metadata
            }
            
            logger.info(f"Successfully uploaded video: {result}")
            return result

        except Exception as e:
            # Clean up temporary file if created and error occurred
            if shorts_video_path != video_path and os.path.exists(shorts_video_path):
                os.remove(shorts_video_path)
            logger.error(f"YouTube upload failed: {str(e)}")
            raise Exception(f"YouTube upload failed: {str(e)}")

    async def get_upload_status(self, video_id: str) -> Dict:
        """Get the status of an uploaded video"""
        youtube = build(
            self.api_service_name,
            self.api_version,
            credentials=self.credentials
        )
        
        request = youtube.videos().list(
            part="status,processingDetails,statistics",
            id=video_id
        )
        
        response = await self._make_api_request(request)
        return response['items'][0] if response['items'] else None

    async def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        language: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """Update video metadata after upload"""
        youtube = build(
            self.api_service_name,
            self.api_version,
            credentials=self.credentials
        )
        
        # Get current video data
        current_data = await self.get_upload_status(video_id)
        
        body = {
            'id': video_id,
            'snippet': {
                'title': title or current_data['snippet']['title'],
                'description': description or current_data['snippet']['description'],
                'tags': tags or current_data['snippet'].get('tags', []),
                'categoryId': self.category_map.get(category, current_data['snippet']['categoryId']),
                'defaultLanguage': language or current_data['snippet'].get('defaultLanguage', 'en')
            }
        }
        
        request = youtube.videos().update(
            part="snippet",
            body=body
        )
        
        response = await self._make_api_request(request)
        return response
