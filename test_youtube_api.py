#!/usr/bin/env python3
"""Test YouTube API integration"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🧪 Testing YouTube Data API Integration")
print("=" * 60)
print()

# Test 1: Check API key
api_key = os.getenv("YOUTUBE_API_KEY")
if api_key:
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-5:]}")
else:
    print("❌ API Key not found in environment")
    exit(1)

print()

# Test 2: Import and initialize
try:
    from youtube_api import YouTubeAPIClient
    print("✅ YouTubeAPIClient imported successfully")
    
    client = YouTubeAPIClient(api_key)
    print("✅ YouTubeAPIClient initialized")
except Exception as e:
    print(f"❌ Import/initialization failed: {e}")
    exit(1)

print()

# Test 3: Search for videos
try:
    print("📺 Searching for: 'League of Legends Miss Fortune guide'")
    videos = client.search_videos('League of Legends Miss Fortune guide', 3)
    
    print(f"✅ Found {len(videos)} videos")
    print()
    
    if videos:
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video.get('title', 'No title')}")
            print(f"   URL: {video.get('url', 'No URL')}")
            print(f"   Views: {video.get('views', 'Unknown')}")
            print(f"   Duration: {video.get('duration', 'Unknown')}")
            print()
        
        print("=" * 60)
        print("🎉 SUCCESS! YouTube Data API is working perfectly!")
        print("=" * 60)
    else:
        print("⚠️  No videos found (might be API issue)")
        
except Exception as e:
    print(f"❌ Search failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
