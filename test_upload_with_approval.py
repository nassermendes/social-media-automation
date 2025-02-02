import requests
import sys
from datetime import datetime, timedelta
import json

def upload_and_approve(video_path):
    # Step 1: Process the video
    url = "http://localhost:8000/process-video"
    with open(video_path, 'rb') as f:
        files = {'video': f}
        response = requests.post(url, files=files)
    
    if response.status_code != 200:
        print("Error processing video:", response.json())
        return
    
    result = response.json()
    if result["status"] != "success":
        print("Error:", result["message"])
        return
    
    # Print generated content for review
    print("\nGenerated Description:")
    print(result["data"]["description"])
    print("\nGenerated Hashtags:")
    print(" ".join(result["data"]["hashtags"]))
    
    # Ask for approval
    approve = input("\nDo you want to approve this content? (yes/no): ")
    if approve.lower() != "yes":
        print("Content rejected. Please try again.")
        return
    
    # Ask for scheduling
    schedule = input("\nDo you want to schedule this post? (yes/no): ")
    schedule_time = None
    if schedule.lower() == "yes":
        hours = int(input("Hours from now to post: "))
        schedule_time = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    
    # Step 2: Post approved content
    platforms = []
    print("\nSelect platforms to post to:")
    print("1. Personal YouTube")
    print("2. Charity YouTube")
    print("3. Personal Instagram")
    print("4. Charity Instagram")
    print("5. Personal TikTok")
    print("6. Charity TikTok")
    
    platform_map = {
        "1": "youtube_personal",
        "2": "youtube_charity",
        "3": "instagram_personal",
        "4": "instagram_charity",
        "5": "tiktok_personal",
        "6": "tiktok_charity"
    }
    
    selections = input("Enter numbers separated by commas (e.g., 1,2,3): ")
    for selection in selections.split(","):
        if selection.strip() in platform_map:
            platforms.append(platform_map[selection.strip()])
    
    # Prepare content for posting
    content = {
        "description": result["data"]["description"],
        "hashtags": result["data"]["hashtags"],
        "platforms": platforms,
        "schedule_time": schedule_time
    }
    
    # Post content
    response = requests.post(
        "http://localhost:8000/approve-and-post",
        data={"temp_path": result["data"]["temp_path"]},
        json=content
    )
    
    if response.status_code != 200:
        print("Error posting content:", response.json())
        return
    
    # Print results
    results = response.json()
    print("\nPosting Results:")
    for platform, status in results.items():
        if status["status"] == "success":
            print(f"{platform}: Successfully posted - {status['url']}")
        else:
            print(f"{platform}: Error - {status['error']}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_upload_with_approval.py path_to_video.mp4")
    else:
        upload_and_approve(sys.argv[1])
