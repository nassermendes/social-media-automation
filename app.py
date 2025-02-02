from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import openai
from moviepy.editor import VideoFileClip
import json
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime, timedelta
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import mimetypes
import asyncio
from pydantic import BaseModel
from enum import Enum

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

class Platform(str, Enum):
    YOUTUBE_PERSONAL = "youtube_personal"
    YOUTUBE_CHARITY = "youtube_charity"
    INSTAGRAM_PERSONAL = "instagram_personal"
    INSTAGRAM_CHARITY = "instagram_charity"
    TIKTOK_PERSONAL = "tiktok_personal"
    TIKTOK_CHARITY = "tiktok_charity"

class ContentApproval(BaseModel):
    description: str
    hashtags: List[str]
    platforms: List[Platform]
    schedule_time: Optional[datetime] = None

class PostStatus(BaseModel):
    platform: Platform
    status: str
    url: Optional[str] = None
    error: Optional[str] = None

class SocialMediaHandler:
    def __init__(self):
        self.youtube_credentials = {
            Platform.YOUTUBE_PERSONAL: self._get_youtube_credentials("PERSONAL"),
            Platform.YOUTUBE_CHARITY: self._get_youtube_credentials("CHARITY")
        }
        self.instagram_tokens = {
            Platform.INSTAGRAM_PERSONAL: {
                "access_token": os.getenv("INSTAGRAM_PERSONAL_ACCESS_TOKEN"),
                "user_id": os.getenv("INSTAGRAM_PERSONAL_USER_ID")
            },
            Platform.INSTAGRAM_CHARITY: {
                "access_token": os.getenv("INSTAGRAM_CHARITY_ACCESS_TOKEN"),
                "user_id": os.getenv("INSTAGRAM_CHARITY_USER_ID")
            }
        }
        self.tiktok_tokens = {
            Platform.TIKTOK_PERSONAL: {
                "client_key": os.getenv("TIKTOK_PERSONAL_CLIENT_KEY"),
                "client_secret": os.getenv("TIKTOK_PERSONAL_CLIENT_SECRET"),
                "access_token": os.getenv("TIKTOK_PERSONAL_ACCESS_TOKEN")
            },
            Platform.TIKTOK_CHARITY: {
                "client_key": os.getenv("TIKTOK_CHARITY_CLIENT_KEY"),
                "client_secret": os.getenv("TIKTOK_CHARITY_CLIENT_SECRET"),
                "access_token": os.getenv("TIKTOK_CHARITY_ACCESS_TOKEN")
            }
        }
        
    def _get_youtube_credentials(self, account_type: str):
        """Get or refresh YouTube credentials for specific account"""
        creds = None
        token_file = f'token_{account_type.lower()}.json'
        
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Try different ports if there's a conflict
                ports = [8090, 8091, 8092, 8093, 8094]
                flow = InstalledAppFlow.from_client_config({
                    "installed": {
                        "client_id": os.getenv(f"YOUTUBE_{account_type}_CLIENT_ID"),
                        "client_secret": os.getenv(f"YOUTUBE_{account_type}_CLIENT_SECRET"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://127.0.0.1"]
                    }
                }, ['https://www.googleapis.com/auth/youtube.upload'])
                
                for port in ports:
                    try:
                        creds = flow.run_local_server(host='127.0.0.1', port=port)
                        break
                    except OSError:
                        if port == ports[-1]:
                            raise Exception("Could not find an available port for OAuth flow")
                        continue
            
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        return creds
        
    async def process_video(self, video_file: UploadFile) -> Dict:
        try:
            # Save uploaded video temporarily
            temp_path = f"temp_{video_file.filename}"
            with open(temp_path, "wb") as f:
                content = await video_file.read()
                f.write(content)
            
            # Extract video frames for analysis
            video = VideoFileClip(temp_path)
            frames = [video.get_frame(t) for t in range(0, int(video.duration), 10)]
            
            # Generate video description using ChatGPT
            description = await self.generate_description(frames)
            
            # Generate hashtags
            hashtags = await self.generate_hashtags(description)
            
            # Clean up
            video.close()
            
            return {
                "temp_path": temp_path,
                "description": description,
                "hashtags": hashtags
            }
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logging.error(f"Error processing video: {str(e)}")
            raise

    async def generate_description(self, frames) -> str:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Create an engaging social media caption for this video. Make it conversational and engaging."
                            },
                            *[{"type": "image", "image": frame.tolist()} for frame in frames[:5]]
                        ],
                    }
                ],
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating description: {str(e)}")
            raise

    async def generate_hashtags(self, description: str) -> List[str]:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate 10 relevant and trending hashtags for this content: {description}"
                    }
                ],
                max_tokens=100
            )
            hashtags = response.choices[0].message.content.split()
            return [tag for tag in hashtags if tag.startswith("#")]
        except Exception as e:
            logging.error(f"Error generating hashtags: {str(e)}")
            raise

    async def post_to_youtube(self, platform: Platform, video_path: str, title: str, description: str, schedule_time: Optional[datetime] = None) -> str:
        """Post video to YouTube as a Short"""
        try:
            youtube = build('youtube', 'v3', credentials=self.youtube_credentials[platform])
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': [],
                    'categoryId': '22'  # People & Blogs category
                },
                'status': {
                    'privacyStatus': 'private' if schedule_time else 'public',
                    'selfDeclaredMadeForKids': False,
                    'publishAt': schedule_time.isoformat() if schedule_time else None
                }
            }
            
            # Get mime type using mimetypes
            mime_type, _ = mimetypes.guess_type(video_path)
            if not mime_type:
                mime_type = 'video/mp4'  # Default to mp4 if we can't detect
            
            # Insert video
            insert_request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=MediaFileUpload(video_path, mimetype=mime_type, resumable=True)
            )
            
            response = insert_request.execute()
            return f"https://youtube.com/shorts/{response['id']}"
            
        except Exception as e:
            logging.error(f"Error posting to YouTube: {str(e)}")
            raise

    async def post_to_instagram(self, platform: Platform, video_path: str, caption: str, schedule_time: Optional[datetime] = None) -> str:
        """Post video to Instagram Reels"""
        try:
            credentials = self.instagram_tokens[platform]
            async with aiohttp.ClientSession() as session:
                # First, upload the video to get a container ID
                params = {
                    'access_token': credentials["access_token"],
                    'media_type': 'REELS',
                    'caption': caption,
                    'share_to_feed': 'true'
                }

                # Upload video to Media Library
                with open(video_path, 'rb') as video_file:
                    files = {'video': video_file}
                    async with session.post(
                        f'https://graph.facebook.com/v18.0/{credentials["user_id"]}/media',
                        params=params,
                        data=files
                    ) as response:
                        container = await response.json()
                        if 'error' in container:
                            raise Exception(f"Failed to upload video: {container['error']['message']}")
                        if 'id' not in container:
                            raise Exception(f"Failed to create media container: {container}")
                
                # Check media status until it's ready
                media_id = container['id']
                for _ in range(30):  # Wait up to 30 seconds
                    async with session.get(
                        f'https://graph.facebook.com/v18.0/{media_id}',
                        params={'access_token': credentials["access_token"]}
                    ) as response:
                        status = await response.json()
                        if status.get('status_code') == 'FINISHED':
                            break
                        elif status.get('status_code') in ['ERROR', 'EXPIRED']:
                            raise Exception(f"Media upload failed: {status.get('status_code')}")
                        await asyncio.sleep(1)
                
                # Publish the container
                publish_params = {
                    'access_token': credentials["access_token"],
                    'creation_id': media_id
                }
                
                if schedule_time:
                    publish_params['published'] = 'false'
                    publish_params['scheduled_publish_time'] = int(schedule_time.timestamp())
                
                async with session.post(
                    f'https://graph.facebook.com/v18.0/{credentials["user_id"]}/media_publish',
                    params=publish_params
                ) as response:
                    result = await response.json()
                    if 'error' in result:
                        raise Exception(f"Failed to publish: {result['error']['message']}")
                    
                return f"https://www.instagram.com/reel/{result.get('id')}"
                
        except Exception as e:
            logging.error(f"Error posting to Instagram: {str(e)}")
            raise

    async def post_to_tiktok(self, platform: Platform, video_path: str, description: str, schedule_time: Optional[datetime] = None) -> str:
        """Post video to TikTok"""
        try:
            credentials = self.tiktok_tokens[platform]
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {credentials["access_token"]}'
                }
                
                # Initialize upload
                params = {
                    'source_info': {
                        'source': 'FILE_UPLOAD',
                        'video_size': os.path.getsize(video_path),
                        'chunk_size': 0
                    }
                }
                
                if schedule_time:
                    params['schedule_time'] = int(schedule_time.timestamp())
                
                async with session.post(
                    'https://open-api.tiktok.com/share/video/upload/',
                    headers=headers,
                    json=params
                ) as response:
                    upload_info = await response.json()
                
                # Upload video file
                with open(video_path, 'rb') as f:
                    files = {'video': f}
                    async with session.post(
                        upload_info['upload_url'],
                        headers=headers,
                        data=files
                    ) as response:
                        result = await response.json()
                
                return f"https://www.tiktok.com/@me/video/{result['video_id']}"
                
        except Exception as e:
            logging.error(f"Error posting to TikTok: {str(e)}")
            raise

handler = SocialMediaHandler()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-video")
async def process_video(video: UploadFile = File(...)):
    """First step: Process video and generate content for approval"""
    try:
        result = await handler.process_video(video)
        return {
            "status": "success",
            "data": {
                "temp_path": result["temp_path"],
                "description": result["description"],
                "hashtags": result["hashtags"]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/approve-and-post")
async def approve_and_post(
    temp_path: str = Form(...),
    content: ContentApproval = Body(...)
) -> Dict[Platform, PostStatus]:
    """Second step: Post approved content to selected platforms"""
    try:
        results = {}
        caption = f"{content.description}\n\n{' '.join(content.hashtags)}"
        
        for platform in content.platforms:
            try:
                if platform in [Platform.YOUTUBE_PERSONAL, Platform.YOUTUBE_CHARITY]:
                    url = await handler.post_to_youtube(
                        platform=platform,
                        video_path=temp_path,
                        title="New Short",  # You might want to generate a title
                        description=caption,
                        schedule_time=content.schedule_time
                    )
                    results[platform] = PostStatus(platform=platform, status="success", url=url)
                    
                elif platform in [Platform.INSTAGRAM_PERSONAL, Platform.INSTAGRAM_CHARITY]:
                    url = await handler.post_to_instagram(
                        platform=platform,
                        video_path=temp_path,
                        caption=caption,
                        schedule_time=content.schedule_time
                    )
                    results[platform] = PostStatus(platform=platform, status="success", url=url)
                    
                elif platform in [Platform.TIKTOK_PERSONAL, Platform.TIKTOK_CHARITY]:
                    url = await handler.post_to_tiktok(
                        platform=platform,
                        video_path=temp_path,
                        description=caption,
                        schedule_time=content.schedule_time
                    )
                    results[platform] = PostStatus(platform=platform, status="success", url=url)
                    
            except Exception as e:
                results[platform] = PostStatus(
                    platform=platform,
                    status="error",
                    error=str(e)
                )
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return results
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))
