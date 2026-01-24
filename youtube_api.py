"""
YouTube Data API Client
More reliable alternative to web scraping
"""

import os
from googleapiclient.discovery import build
from typing import List, Dict


class YouTubeAPIClient:
    """YouTube Data API v3 client"""
    
    def __init__(self, api_key: str = None):
        """Initialize with API key from environment or parameter"""
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key required")
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    def search_videos(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search YouTube videos using official API
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of video dictionaries
        """
        try:
            # Search for videos
            search_response = self.youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                order='relevance',
                videoDefinition='any'
            ).execute()
            
            videos = []
            video_ids = []
            
            # Extract video IDs and basic info
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                video_ids.append(video_id)
                
                snippet = item['snippet']
                videos.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'channel': snippet['channelTitle'],
                    'description': snippet['description'],
                    'thumbnail': snippet['thumbnails']['high']['url'],
                    'published_at': snippet['publishedAt']
                })
            
            # Get additional statistics (views, duration)
            if video_ids:
                video_response = self.youtube.videos().list(
                    part='statistics,contentDetails',
                    id=','.join(video_ids)
                ).execute()
                
                for i, video_item in enumerate(video_response.get('items', [])):
                    stats = video_item['statistics']
                    duration = video_item['contentDetails']['duration']
                    
                    videos[i]['views'] = int(stats.get('viewCount', 0))
                    videos[i]['views_text'] = f"{int(stats.get('viewCount', 0)):,} views"
                    videos[i]['likes'] = int(stats.get('likeCount', 0))
                    videos[i]['duration'] = self._parse_duration(duration)
                    videos[i]['url'] = f"https://www.youtube.com/watch?v={videos[i]['video_id']}"
            
            print(f"✅ Found {len(videos)} videos via YouTube API")
            return videos
            
        except Exception as e:
            print(f"❌ YouTube API error: {e}")
            return []
    
    def _parse_duration(self, duration: str) -> str:
        """Convert ISO 8601 duration to readable format (PT1H2M10S -> 1:02:10)"""
        import re
        
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return "N/A"
        
        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def format_video_list(self, videos: List[Dict]) -> str:
        """Format video list for display"""
        if not videos:
            return "No videos found."
        
        result = ""
        for i, video in enumerate(videos, 1):
            views_k = video.get('views', 0) / 1000
            result += f"{i}. **{video['title']}**\n"
            result += f"   • Channel: {video['channel']}\n"
            result += f"   • Duration: {video.get('duration', 'N/A')} | Views: {views_k:.1f}K\n"
            result += f"   • Link: {video['url']}\n\n"
        
        return result


# For backwards compatibility
class YouTubeScraper(YouTubeAPIClient):
    """Alias for backwards compatibility"""
    pass
