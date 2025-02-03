# Social Media Automation Tool

A powerful automation tool for managing and uploading videos across multiple social media platforms (YouTube, Instagram, and TikTok).

## Features

- **Multi-Platform Support**
  - YouTube Shorts
  - Instagram Reels
  - TikTok Videos
  
- **Multiple Account Management**
  - Support for both personal and charity accounts
  - Secure credential management
  
- **Smart Video Processing**
  - Automatic video optimization for each platform
  - Aspect ratio adjustment (9:16 for vertical content)
  - Quality and file size optimization
  - Duration limits handling
  
- **ChatGPT Integration**
  - Content optimization
  - Caption generation
  - Hashtag recommendations
  
- **Advanced Features**
  - Progress tracking
  - Retry logic for reliability
  - Detailed error handling
  - Temporary file cleanup
  - Comprehensive logging

## Flow

1. **Video Upload**
   - User selects video file
   - System validates format and size
   - Video is processed for platform requirements

2. **Video Processing**
   - Aspect ratio adjustment (9:16)
   - Duration check and trimming
   - Quality optimization
   - File size optimization

3. **Content Generation**
   - ChatGPT generates optimized captions
   - Platform-specific hashtags added
   - Content compliance check

4. **Platform Upload**
   - YouTube: Upload as Shorts with proper categorization
   - Instagram: Upload as Reels with location/mentions
   - TikTok: Upload with proper settings and sharing options

5. **Status Tracking**
   - Upload progress monitoring
   - Processing status updates
   - Error handling and retries
   - Success confirmation

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/social-media-automation.git
cd social-media-automation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

4. Run the application:
```bash
python app.py
```

## Environment Variables

Required environment variables in `.env`:

```
# YouTube Credentials
YOUTUBE_PERSONAL_CLIENT_ID=
YOUTUBE_PERSONAL_CLIENT_SECRET=
YOUTUBE_CHARITY_CLIENT_ID=
YOUTUBE_CHARITY_CLIENT_SECRET=

# Instagram Credentials
INSTAGRAM_PERSONAL_ACCESS_TOKEN=
INSTAGRAM_PERSONAL_USER_ID=
INSTAGRAM_CHARITY_ACCESS_TOKEN=
INSTAGRAM_CHARITY_USER_ID=

# TikTok Credentials
TIKTOK_APP_KEY=
TIKTOK_APP_SECRET=
TIKTOK_PERSONAL_CLIENT_KEY=
TIKTOK_PERSONAL_CLIENT_SECRET=
TIKTOK_PERSONAL_ACCESS_TOKEN=
TIKTOK_CHARITY_CLIENT_KEY=
TIKTOK_CHARITY_CLIENT_SECRET=
TIKTOK_CHARITY_ACCESS_TOKEN=

# OpenAI (ChatGPT) Credentials
OPENAI_API_KEY=
```

## Project Structure

```
social-media-automation/
├── api/
│   └── src/
│       ├── services/
│       │   └── platforms/
│       │       ├── youtube.py
│       │       ├── instagram.py
│       │       └── tiktok.py
│       ├── routes/
│       └── config.py
├── static/
├── templates/
├── app.py
├── requirements.txt
└── .env
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
