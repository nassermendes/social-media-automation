import asyncio
from app import SocialMediaPoster, Platform

async def test_instagram_upload():
    poster = SocialMediaPoster()
    
    # Path to your test video
    video_path = "test_video.mp4"  # Make sure this file exists
    caption = "Test upload to Instagram Reels! 🎥 #test #automation"
    
    try:
        # Upload to personal account
        result = await poster.post_to_instagram(
            Platform.PERSONAL,
            video_path,
            caption
        )
        print(f"Successfully uploaded to Instagram! View at: {result}")
    except Exception as e:
        print(f"Error uploading to Instagram: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_instagram_upload())
