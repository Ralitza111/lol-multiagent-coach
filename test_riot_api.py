#!/usr/bin/env python3
"""Quick test script to verify Riot API works"""
from dotenv import load_dotenv
import os
from riot_api import RiotAPI

load_dotenv()

riot_api_key = os.getenv('RIOT_API_KEY')
riot_api = RiotAPI(api_key=riot_api_key, region='na1', routing='americas')

print(f"Testing with API key: {riot_api_key[:30]}...")
print(f"Looking up: BeLikeThatOrElse#NA1\n")

account = riot_api.get_account_by_riot_id("BeLikeThatOrElse", "NA1")

if account:
    print("✅ SUCCESS!")
    print(f"   Game Name: {account.get('gameName')}")
    print(f"   Tag Line: {account.get('tagLine')}")
    print(f"   PUUID: {account.get('puuid')[:20]}...")
else:
    print("❌ FAILED - Check error messages above")
