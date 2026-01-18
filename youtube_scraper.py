"""
YouTube Web Scraper
Alternative to YouTube Data API - scrapes video data directly from YouTube pages
Useful as backup when API quota is exceeded or for additional metadata
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import json
from urllib.parse import quote_plus, urljoin


class YouTubeScraper:
    """Scrape YouTube video data without using API quota"""
    
    BASE_URL = "https://www.youtube.com"
    SEARCH_URL = f"{BASE_URL}/results"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def search_videos(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search YouTube and scrape video results
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
        
        Returns:
            List of video dictionaries
        """
        try:
            # Construct search URL
            encoded_query = quote_plus(query)
            url = f"{self.SEARCH_URL}?search_query={encoded_query}"
            
            print(f"🔍 Scraping YouTube search: {query}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # YouTube embeds data in JavaScript - extract it
            videos = self._extract_video_data(soup, max_results)
            
            if not videos:
                print("⚠️  No videos found via scraping, trying alternative method")
                videos = self._extract_from_scripts(response.text, max_results)
            
            print(f"✅ Scraped {len(videos)} videos from YouTube")
            return videos[:max_results]
            
        except Exception as e:
            print(f"❌ YouTube scraping error: {e}")
            return []
    
    def _extract_video_data(self, soup: BeautifulSoup, max_results: int) -> List[Dict]:
        """Extract video data from HTML elements"""
        videos = []
        
        try:
            # YouTube uses various class names - try multiple patterns
            video_selectors = [
                'ytd-video-renderer',
                'ytd-playlist-video-renderer',
                'ytd-grid-video-renderer'
            ]
            
            for selector in video_selectors:
                video_elements = soup.find_all(selector)
                
                for element in video_elements[:max_results]:
                    if len(videos) >= max_results:
                        break
                    
                    try:
                        video_data = self._parse_video_element(element)
                        if video_data:
                            videos.append(video_data)
                    except Exception as e:
                        print(f"⚠️  Error parsing video element: {e}")
                        continue
                
                if videos:
                    break  # Found videos, no need to try other selectors
            
            return videos
            
        except Exception as e:
            print(f"⚠️  HTML extraction error: {e}")
            return []
    
    def _parse_video_element(self, element) -> Optional[Dict]:
        """Parse individual video element"""
        try:
            # Extract video ID
            video_link = element.find('a', id='video-title')
            if not video_link:
                return None
            
            video_id = None
            href = video_link.get('href', '')
            if '/watch?v=' in href:
                video_id = href.split('/watch?v=')[1].split('&')[0]
            
            if not video_id:
                return None
            
            # Extract title
            title = video_link.get('title', '') or video_link.get_text(strip=True)
            
            # Extract channel name
            channel_elem = element.find('ytd-channel-name') or element.find('a', class_='yt-simple-endpoint')
            channel = channel_elem.get_text(strip=True) if channel_elem else 'Unknown'
            
            # Extract view count and duration
            metadata = element.find_all('span', class_='style-scope ytd-video-meta-block')
            views_text = 'N/A'
            duration = 'N/A'
            
            for meta in metadata:
                text = meta.get_text(strip=True)
                if 'view' in text.lower():
                    views_text = text
                elif ':' in text:
                    duration = text
            
            # Extract thumbnail
            thumbnail_elem = element.find('img')
            thumbnail = thumbnail_elem.get('src', '') if thumbnail_elem else ''
            
            # Parse view count
            views = self._parse_view_count(views_text)
            
            return {
                'video_id': video_id,
                'title': title,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'channel': channel,
                'views': views,
                'views_text': views_text,
                'duration': duration,
                'thumbnail': thumbnail,
                'description': title[:200] + '...',  # Use title as description
            }
            
        except Exception as e:
            print(f"⚠️  Parse element error: {e}")
            return None
    
    def _extract_from_scripts(self, html_text: str, max_results: int) -> List[Dict]:
        """Extract video data from embedded JavaScript"""
        videos = []
        
        try:
            # YouTube embeds data in ytInitialData variable
            pattern = r'var ytInitialData = ({.*?});'
            match = re.search(pattern, html_text, re.DOTALL)
            
            if match:
                try:
                    data = json.loads(match.group(1))
                    
                    # Navigate YouTube's data structure
                    contents = (data.get('contents', {})
                               .get('twoColumnSearchResultsRenderer', {})
                               .get('primaryContents', {})
                               .get('sectionListRenderer', {})
                               .get('contents', []))
                    
                    for section in contents:
                        item_section = section.get('itemSectionRenderer', {})
                        video_items = item_section.get('contents', [])
                        
                        for item in video_items[:max_results]:
                            if len(videos) >= max_results:
                                break
                            
                            video_renderer = item.get('videoRenderer')
                            if video_renderer:
                                video_data = self._parse_video_renderer(video_renderer)
                                if video_data:
                                    videos.append(video_data)
                
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON decode error: {e}")
            
            return videos
            
        except Exception as e:
            print(f"⚠️  Script extraction error: {e}")
            return []
    
    def _parse_video_renderer(self, renderer: Dict) -> Optional[Dict]:
        """Parse video data from ytInitialData structure"""
        try:
            video_id = renderer.get('videoId')
            if not video_id:
                return None
            
            # Extract title
            title_runs = renderer.get('title', {}).get('runs', [])
            title = title_runs[0].get('text', 'Unknown') if title_runs else 'Unknown'
            
            # Extract channel
            owner_text = renderer.get('ownerText', {}).get('runs', [])
            channel = owner_text[0].get('text', 'Unknown') if owner_text else 'Unknown'
            
            # Extract view count
            view_count_text = renderer.get('viewCountText', {}).get('simpleText', '0 views')
            views = self._parse_view_count(view_count_text)
            
            # Extract duration
            length_text = renderer.get('lengthText', {}).get('simpleText', 'N/A')
            
            # Extract thumbnail
            thumbnails = renderer.get('thumbnail', {}).get('thumbnails', [])
            thumbnail = thumbnails[-1].get('url', '') if thumbnails else ''
            
            return {
                'video_id': video_id,
                'title': title,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'channel': channel,
                'views': views,
                'views_text': view_count_text,
                'duration': length_text,
                'thumbnail': thumbnail,
                'description': title[:200] + '...',
            }
            
        except Exception as e:
            print(f"⚠️  Renderer parse error: {e}")
            return None
    
    def _parse_view_count(self, view_text: str) -> int:
        """Parse view count from text like '1.2M views' or '50K views'"""
        try:
            # Remove 'views' and extra spaces
            view_text = view_text.lower().replace('views', '').replace('view', '').strip()
            
            # Handle K, M, B suffixes
            multipliers = {
                'k': 1_000,
                'm': 1_000_000,
                'b': 1_000_000_000
            }
            
            for suffix, multiplier in multipliers.items():
                if suffix in view_text:
                    number = float(view_text.replace(suffix, '').strip())
                    return int(number * multiplier)
            
            # Try to parse as plain number
            view_text = re.sub(r'[^\d.]', '', view_text)
            return int(float(view_text)) if view_text else 0
            
        except Exception:
            return 0
    
    def format_video_list(self, videos: List[Dict]) -> str:
        """Format video list for display"""
        if not videos:
            return "No videos found."
        
        result = ""
        for i, video in enumerate(videos, 1):
            views_k = video['views'] / 1000 if video['views'] > 0 else 0
            result += f"{i}. **{video['title']}**\n"
            result += f"   • Channel: {video['channel']}\n"
            result += f"   • Duration: {video['duration']} | Views: {views_k:.1f}K\n"
            result += f"   • Link: {video['url']}\n\n"
        
        return result


# Test the scraper
if __name__ == "__main__":
    print("🎬 Testing YouTube Scraper\n")
    
    scraper = YouTubeScraper()
    
    # Test searches
    test_queries = [
        "League of Legends Ahri guide 2024",
        "Ahri vs Zed gameplay",
        "League wave management tutorial"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: {query}")
        print('='*60)
        
        videos = scraper.search_videos(query, max_results=3)
        
        if videos:
            print(f"✅ Found {len(videos)} videos:\n")
            print(scraper.format_video_list(videos))
        else:
            print("❌ No videos found")
        
        print()
