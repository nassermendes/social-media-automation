from openai import OpenAI
from typing import Dict, List
from ..config import get_settings

settings = get_settings()

class ContentGenerationService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_content(self, video_analysis: Dict, platforms: List[str]) -> Dict:
        """Generate platform-specific content using video analysis data"""
        
        # Create a detailed prompt from video analysis
        prompt = self._create_prompt(video_analysis, platforms)
        
        # Get completion from GPT-4
        response = await self._get_completion(prompt)
        
        # Parse and format the response
        return self._parse_response(response, platforms)

    def _create_prompt(self, analysis: Dict, platforms: List[str]) -> str:
        """Create a detailed prompt for GPT based on video analysis"""
        
        # Extract key information from analysis
        labels = ", ".join([label["description"] for label in analysis["labels"][:5]])
        duration = analysis["metadata"]["duration"]
        transcription = analysis.get("transcription", [{}])[0].get("transcript", "No transcription available")
        
        prompt = f"""As a social media content expert, create engaging content for a video with the following details:

Video Analysis:
- Main topics/objects: {labels}
- Duration: {duration} seconds
- Transcription: {transcription}

For each platform ({", ".join(platforms)}), generate:
1. An attention-grabbing title/caption
2. A compelling description that drives engagement
3. Relevant hashtags (up to 10 for Instagram/TikTok, 5 for YouTube)
4. Any platform-specific optimizations

Format the response as JSON with the following structure for each platform:
{{
    "platform_name": {{
        "title": "The title",
        "description": "The description",
        "hashtags": ["tag1", "tag2"]
    }}
}}

Consider these platform-specific requirements:
- YouTube: SEO-optimized title and description, include timestamps for videos > 5 minutes
- Instagram: Emoji-friendly, engaging caption, mix of popular and niche hashtags
- TikTok: Trendy, casual tone, relevant trending hashtags

Make the content feel authentic and engaging while maintaining the video's core message."""

        return prompt

    async def _get_completion(self, prompt: str) -> str:
        """Get completion from GPT-4"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media content expert who creates engaging, platform-optimized content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error getting completion from GPT: {str(e)}")

    def _parse_response(self, response: str, platforms: List[str]) -> Dict:
        """Parse and validate GPT's response"""
        try:
            content = json.loads(response)
            
            # Validate and format the response
            formatted_content = {}
            for platform in platforms:
                if platform.lower() in content:
                    platform_content = content[platform.lower()]
                    formatted_content[platform] = {
                        "title": platform_content.get("title", ""),
                        "description": platform_content.get("description", ""),
                        "hashtags": platform_content.get("hashtags", [])
                    }
            
            return formatted_content
        except json.JSONDecodeError:
            raise Exception("Error parsing GPT response: Invalid JSON format")
        except Exception as e:
            raise Exception(f"Error processing GPT response: {str(e)}")
