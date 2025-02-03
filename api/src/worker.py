import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from .services.upload_manager import UploadManager

async def process_uploads():
    """Background worker to process uploads"""
    while True:
        try:
            db = SessionLocal()
            manager = UploadManager(db)
            
            # Process scheduled uploads
            await manager.process_scheduled()
            
            # Process queue
            await manager.process_queue()
            
        except Exception as e:
            print(f"Error processing uploads: {str(e)}")
        
        finally:
            db.close()
        
        # Wait before next check
        await asyncio.sleep(60)  # Check every minute

def start_worker():
    """Start the background worker"""
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(process_uploads())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    start_worker()
