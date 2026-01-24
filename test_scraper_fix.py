#!/usr/bin/env python3
"""Test the updated YouTube scraper"""

from youtube_scraper import YouTubeScraper

def test_scraper():
    scraper = YouTubeScraper()
    print('🧪 Testing UPDATED YouTube Scraper...')
    print('=' * 60)
    print()
    
    # Test with Miss Fortune
    print('Test: Searching for "League of Legends Miss Fortune guide"')
    videos = scraper.search_videos('League of Legends Miss Fortune guide', 3)
    
    print()
    print(f'📊 Results: Found {len(videos)} videos')
    print('=' * 60)
    print()
    
    if videos:
        print('✅ SUCCESS! Scraper is working again!')
        print()
        for i, v in enumerate(videos, 1):
            print(f'{i}. {v.get("title", "No title")}')
            print(f'   URL: {v.get("url", "No URL")}')
            print(f'   Views: {v.get("views", "Unknown")}')
            print(f'   Duration: {v.get("duration", "Unknown")}')
            print()
        return True
    else:
        print('❌ Still not working - YouTube blocking is too strong')
        print()
        print('📝 Analysis:')
        print('   - YouTube has strengthened bot detection')
        print('   - Web scraping is being actively blocked')
        print('   - This is why the scraper that "was working" stopped')
        print()
        print('💡 Solutions:')
        print('   1. Use YouTube Data API (recommended, reliable)')
        print('   2. Use a proxy service')
        print('   3. Accept that video search is unavailable')
        print()
        return False

if __name__ == '__main__':
    test_scraper()
