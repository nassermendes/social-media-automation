from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import random
from typing import Dict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Store upload progress
upload_progress: Dict[str, Dict[str, any]] = {
    'youtube-personal': {'progress': 0, 'status': 'idle', 'error': None},
    'youtube-charity': {'progress': 0, 'status': 'idle', 'error': None},
    'instagram-personal': {'progress': 0, 'status': 'idle', 'error': None},
    'instagram-charity': {'progress': 0, 'status': 'idle', 'error': None},
    'tiktok-personal': {'progress': 0, 'status': 'idle', 'error': None},
    'tiktok-charity': {'progress': 0, 'status': 'idle', 'error': None}
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    logger.debug("Serving home page")
    try:
        return templates.TemplateResponse(
            "index.html",
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving home page: {str(e)}")
        raise

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    logger.debug("Starting file upload")
    # Reset progress
    for platform in upload_progress:
        upload_progress[platform] = {'progress': 0, 'status': 'uploading', 'error': None}
    
    # Simulate file processing
    content = await file.read()
    
    # Start progress monitoring
    return {"message": "Upload started"}

@app.get("/progress")
async def progress():
    logger.debug("Starting progress monitoring")
    async def generate_progress():
        try:
            for progress in range(0, 101, 5):
                # Update progress for each platform
                for platform in upload_progress:
                    # Simulate random delays and errors
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    if progress == 100:
                        # Simulate random failures
                        if random.random() < 0.2:  # 20% chance of failure
                            upload_progress[platform] = {
                                'progress': progress,
                                'status': 'error',
                                'error': 'Upload failed. Click to retry.'
                            }
                        else:
                            upload_progress[platform] = {
                                'progress': progress,
                                'status': 'success',
                                'error': None
                            }
                    else:
                        upload_progress[platform]['progress'] = progress
                
                # Send progress update
                yield f"data: {json.dumps(upload_progress)}\n\n"
                
            # Send completion message
            yield f"data: {json.dumps({'complete': True})}\n\n"
                
        except asyncio.CancelledError:
            logger.warning("Progress monitoring cancelled")
            pass
        except Exception as e:
            logger.error(f"Error in progress monitoring: {str(e)}")
            raise

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream"
    )

@app.get("/platform/{platform_id}")
async def platform_error(platform_id: str):
    logger.debug(f"Getting error details for platform: {platform_id}")
    # This would normally show platform-specific error details
    return {"message": f"Error details for {platform_id}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
