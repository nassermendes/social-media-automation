import requests
import sys

def upload_video(video_path):
    url = "http://localhost:8000/process-video"
    params = {"platforms": "youtube"}
    
    with open(video_path, 'rb') as f:
        files = {'video': f}
        response = requests.post(url, params=params, files=files)
    
    print(response.json())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_upload.py path_to_video.mp4")
    else:
        upload_video(sys.argv[1])
