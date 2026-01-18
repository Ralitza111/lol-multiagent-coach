"""
Riot Games API Integration

Handles all interactions with the Riot Games API for fetching summoner data,
match history, and game statistics.
"""

import requests
import time
from typing import Dict, List, Optional


class RiotAPI:
    """Wrapper for Riot Games API calls"""
    
    def __init__(self, api_key: str, region: str = "na1", routing: str = "americas"):
        """
        Initialize Riot API client
        
        Args:
            api_key: Riot Games API key from developer.riotgames.com
            region: Platform routing (na1, euw1, kr, etc.)
            routing: Regional routing (americas, europe, asia, sea)
        """
        self.api_key = api_key
        self.region = region
        self.routing = routing
        self.base_url = f"https://{region}.api.riotgames.com"
        self.routing_url = f"https://{routing}.api.riotgames.com"
        self.headers = {"X-Riot-Token": api_key}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.05  # 50ms between requests
    
    def _rate_limit(self):
        """Implement basic rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """Make API request with error handling"""
        self._rate_limit()
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"❌ Not found: {url}")
                return None
            elif response.status_code == 429:
                print("⚠️  Rate limit exceeded. Waiting...")
                time.sleep(2)
                return self._make_request(url)
            elif response.status_code == 403:
                print("❌ Invalid API key or expired")
                return None
            else:
                print(f"❌ API Error {response.status_code}: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            return None
    
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
        """
        Get account information by Riot ID (game name + tag line)
        This is the new Riot ID system that replaced summoner names
        
        Args:
            game_name: The game name (e.g., "BeLikeThatOrElse")
            tag_line: The tag line (e.g., "NA1")
        
        Returns:
            Dict with keys: puuid, gameName, tagLine
        """
        url = f"{self.routing_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return self._make_request(url)
    
    def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict]:
        """
        Get summoner information by PUUID
        
        Returns:
            Dict with keys: id, accountId, puuid, name, summonerLevel, etc.
        """
        url = f"{self.base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return self._make_request(url)
    
    def get_summoner_by_name(self, summoner_name: str) -> Optional[Dict]:
        """
        Get summoner information by summoner name (DEPRECATED - use Riot ID instead)
        
        Returns:
            Dict with keys: id, accountId, puuid, name, summonerLevel, etc.
        """
        url = f"{self.base_url}/lol/summoner/v4/summoners/by-name/{summoner_name}"
        return self._make_request(url)
    
    def get_ranked_stats(self, summoner_id: str) -> Optional[List[Dict]]:
        """
        Get ranked statistics for a summoner
        
        Returns:
            List of ranked queue info (Solo/Duo, Flex, etc.)
        """
        url = f"{self.base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
        return self._make_request(url)
    
    def get_match_history(self, puuid: str, count: int = 20, queue: int = None) -> Optional[List[str]]:
        """
        Get match history IDs for a summoner
        
        Args:
            puuid: Player UUID
            count: Number of matches to retrieve (max 100)
            queue: Queue ID filter (420=Ranked Solo, 400=Normal Draft, etc.)
        
        Returns:
            List of match IDs
        """
        url = f"{self.routing_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
        if queue:
            url += f"&queue={queue}"
        return self._make_request(url)
    
    def get_match_details(self, match_id: str, puuid: str = None) -> Optional[Dict]:
        """
        Get detailed information about a match
        
        Args:
            match_id: Match ID
            puuid: If provided, returns only this player's stats
        
        Returns:
            Match details or player-specific stats if puuid provided
        """
        url = f"{self.routing_url}/lol/match/v5/matches/{match_id}"
        match_data = self._make_request(url)
        
        if not match_data:
            return None
        
        # If puuid specified, extract only that player's data
        if puuid:
            participants = match_data.get('info', {}).get('participants', [])
            for participant in participants:
                if participant.get('puuid') == puuid:
                    return self._format_player_stats(participant)
            return None
        
        return match_data
    
    def get_match_with_enemies(self, match_id: str, puuid: str) -> Optional[Dict]:
        """
        Get match details including enemy team information
        
        Args:
            match_id: Match ID
            puuid: Player's UUID to identify their team
        
        Returns:
            Dict with player stats and enemy team data
        """
        url = f"{self.routing_url}/lol/match/v5/matches/{match_id}"
        match_data = self._make_request(url)
        
        if not match_data:
            return None
        
        participants = match_data.get('info', {}).get('participants', [])
        
        # Find player and their team
        player_data = None
        player_team = None
        
        for participant in participants:
            if participant.get('puuid') == puuid:
                player_data = self._format_player_stats(participant)
                player_team = participant.get('teamId')
                break
        
        if not player_data:
            return None
        
        # Get enemy team
        enemies = []
        for participant in participants:
            if participant.get('teamId') != player_team:
                enemies.append({
                    'champion': participant.get('championName', 'Unknown'),
                    'role': participant.get('teamPosition', 'Unknown'),
                    'kills': participant.get('kills', 0),
                    'deaths': participant.get('deaths', 0),
                    'assists': participant.get('assists', 0),
                })
        
        return {
            'player': player_data,
            'enemies': enemies,
            'game_duration': match_data.get('info', {}).get('gameDuration', 0),
        }
    
    def _format_player_stats(self, participant: Dict) -> Dict:
        """Format participant data into clean stats"""
        return {
            'champion': participant.get('championName', 'Unknown'),
            'kills': participant.get('kills', 0),
            'deaths': participant.get('deaths', 0),
            'assists': participant.get('assists', 0),
            'cs': participant.get('totalMinionsKilled', 0) + participant.get('neutralMinionsKilled', 0),
            'damage': participant.get('totalDamageDealtToChampions', 0),
            'gold': participant.get('goldEarned', 0),
            'vision_score': participant.get('visionScore', 0),
            'win': participant.get('win', False),
            'items': [
                self._get_item_name(participant.get(f'item{i}', 0))
                for i in range(7)
            ],
            'summoner_spells': [
                participant.get('summoner1Id'),
                participant.get('summoner2Id')
            ],
            'role': participant.get('teamPosition', 'Unknown'),
            'game_duration': participant.get('gameDuration', 0),
        }
    
    def _get_item_name(self, item_id: int) -> str:
        """Convert item ID to name (simplified, would need Data Dragon for full names)"""
        if item_id == 0:
            return "Empty"
        return f"Item {item_id}"
    
    def get_champion_mastery(self, puuid: str, champion_id: int = None) -> Optional[Dict]:
        """
        Get champion mastery information
        
        Args:
            puuid: Player UUID
            champion_id: Specific champion ID, or None for all
        
        Returns:
            Champion mastery data
        """
        if champion_id:
            url = f"{self.base_url}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}"
        else:
            url = f"{self.base_url}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        return self._make_request(url)
    
    def get_current_game(self, summoner_id: str) -> Optional[Dict]:
        """
        Get information about a summoner's current active game
        
        Returns:
            Current game info or None if not in game
        """
        url = f"{self.base_url}/lol/spectator/v4/active-games/by-summoner/{summoner_id}"
        return self._make_request(url)


# Utility functions

def calculate_kda(kills: int, deaths: int, assists: int) -> float:
    """Calculate KDA ratio"""
    if deaths == 0:
        return float(kills + assists)
    return (kills + assists) / deaths


def calculate_cs_per_min(cs: int, game_duration: int) -> float:
    """Calculate CS per minute"""
    if game_duration == 0:
        return 0.0
    minutes = game_duration / 60
    return cs / minutes


def get_rank_tier(tier: str, division: str) -> int:
    """Convert rank to numeric tier for comparison"""
    tier_values = {
        'IRON': 0, 'BRONZE': 1, 'SILVER': 2, 'GOLD': 3,
        'PLATINUM': 4, 'EMERALD': 5, 'DIAMOND': 6,
        'MASTER': 7, 'GRANDMASTER': 8, 'CHALLENGER': 9
    }
    division_values = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}
    
    tier_value = tier_values.get(tier.upper(), 0) * 4
    div_value = division_values.get(division, 0)
    
    return tier_value + div_value
