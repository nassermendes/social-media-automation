# Social Media Automation Tool

A powerful automation tool for uploading and managing videos across multiple social media platforms (YouTube, Instagram, and TikTok) with ChatGPT integration for content optimization.

## Features

- **Multi-Platform Support**
  - YouTube Shorts
  - Instagram Reels
  - TikTok Videos
- **Multiple Account Management**
  - Support for both personal and charity accounts
  - Secure credential management
- **Smart Video Processing**
  - Automatic format adaptation for each platform
  - Aspect ratio optimization (9:16 for vertical content)
  - Quality and size optimization
- **ChatGPT Integration**
  - Content optimization
  - Caption generation
  - Hashtag recommendations
- **Robust Error Handling**
  - Automatic retries for failed uploads
  - Detailed error reporting
  - Progress tracking

## Project Structure

```
social-media-automation/
├── api/                    # Backend API
│   └── src/
│       ├── services/      # Platform-specific services
│       │   └── platforms/
│       │       ├── youtube.py    # YouTube integration
│       │       ├── instagram.py  # Instagram integration
│       │       └── tiktok.py     # TikTok integration
│       ├── routes/        # API endpoints
│       └── models.py      # Data models
├── static/                # Static assets
├── templates/             # HTML templates
├── app.py                # Main application file
└── requirements.txt      # Python dependencies
```

## Flow

1. **Video Upload**
   - User submits video through web interface
   - System validates file format and size
   - Video is temporarily stored for processing

2. **Video Processing**
   - Video is analyzed for dimensions and duration
   - Format is optimized for each target platform
   - Temporary versions are created if needed

3. **Content Generation**
   - ChatGPT analyzes video content
   - Generates optimized titles and descriptions
   - Suggests relevant hashtags

4. **Platform Upload**
   - Videos are uploaded to selected platforms
   - Platform-specific requirements are handled
   - Progress is tracked and reported
   - Retry logic handles temporary failures

5. **Status Tracking**
   - Upload status is monitored
   - Success/failure notifications
   - Detailed error reporting if needed

## Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/social-media-automation.git
cd social-media-automation
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

4. Run the application
```bash
python app.py
```

## Environment Variables

Required environment variables in `.env`:

```
# General
OPENAI_API_KEY=your_openai_api_key

# YouTube
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_PERSONAL_REFRESH_TOKEN=your_personal_refresh_token
YOUTUBE_CHARITY_REFRESH_TOKEN=your_charity_refresh_token

# Instagram
INSTAGRAM_PERSONAL_ACCESS_TOKEN=your_personal_access_token
INSTAGRAM_PERSONAL_USER_ID=your_personal_user_id
INSTAGRAM_CHARITY_ACCESS_TOKEN=your_charity_access_token
INSTAGRAM_CHARITY_USER_ID=your_charity_user_id

# TikTok
TIKTOK_APP_KEY=your_app_key
TIKTOK_APP_SECRET=your_app_secret
TIKTOK_PERSONAL_ACCESS_TOKEN=your_personal_access_token
TIKTOK_CHARITY_ACCESS_TOKEN=your_charity_access_token
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
