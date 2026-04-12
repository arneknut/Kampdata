#!/usr/bin/env python3
"""
Script to parse response from NBF Bandy Tournament Player API
Endpoint: https://api.app04.nbf.clh.no/api/v1/nbf/bandy/tournament/players/439465
"""

import requests
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PlayerStats:
    """Data class for player statistics"""
    goals: int = 0
    assists: int = 0
    penalties: int = 0
    games_played: int = 0


@dataclass
class Team:
    """Data class for team information"""
    id: int
    name: str


@dataclass
class Player:
    """Data class for player information"""
    id: int
    first_name: str
    last_name: str
    position: Optional[str]
    jersey_number: Optional[int]
    team: Optional[Team]
    stats: PlayerStats


class BandyAPIParser:
    """Parser for NBF Bandy Tournament API responses"""
    
    BASE_URL = "https://api.app04.nbf.clh.no/api/v1/nbf/bandy/tournament/players"
    
    def __init__(self, timeout: int = 10):
        """Initialize the parser with optional timeout"""
        self.timeout = timeout
        self.session = requests.Session()
    
    def fetch_player(self, player_id: int, ttl: int = 180) -> Optional[Dict[str, Any]]:
        """
        Fetch player data from the API
        
        Args:
            player_id: The player ID to fetch
            ttl: Time to live parameter (cache timeout in seconds)
            
        Returns:
            Raw JSON response as dictionary, or None if request fails
        """
        url = f"{self.BASE_URL}/{player_id}"
        params = {"ttl": ttl}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching player data: {e}")
            return None
    
    def parse_response(self, data: Dict[str, Any]) -> Player:
        """
        Parse the API response into a Player object
        
        Args:
            data: Raw JSON response from the API
            
        Returns:
            Player object with parsed data
        """
        # Extract player information (adapt field names as needed)
        player_id = data.get("personId") or data.get("playerId")
        first_name = data.get("firstName") or data.get("first_name") or ""
        last_name = data.get("lastName") or data.get("last_name") or ""
        position = data.get("position")
        jersey_number = data.get("jerseyNumber") or data.get("jersey_number")
        
        # Parse team information if available
        team = None
        if "team" in data:
            team_data = data["team"]
            team = Team(
                id=team_data.get("id", 0),
                name=team_data.get("name", "Unknown")
            )
        
        # Parse statistics if available
        stats_data = data.get("statistics", {})
        stats = PlayerStats(
            goals=stats_data.get("goals", 0),
            assists=stats_data.get("assists", 0),
            penalties=stats_data.get("penalties", 0),
            games_played=stats_data.get("gamesPlayed") or stats_data.get("games_played", 0)
        )
        
        return Player(
            id=player_id,
            first_name=first_name,
            last_name=last_name,
            position=position,
            jersey_number=jersey_number,
            team=team,
            stats=stats
        )
    
    def get_player_info(self, player_id: int, ttl: int = 180) -> Optional[Player]:
        """
        Fetch and parse player information in one call
        
        Args:
            player_id: The player ID to fetch
            ttl: Time to live parameter
            
        Returns:
            Player object or None if request fails
        """
        raw_data = self.fetch_player(player_id, ttl)
        if raw_data:
            return self.parse_response(raw_data)
        return None
    
    def print_player_info(self, player: Player) -> None:
        """Pretty print player information"""
        print(f"\n{'='*50}")
        print(f"Player Information")
        print(f"{'='*50}")
        print(f"ID: {player.id}")
        print(f"Name: {player.first_name} {player.last_name}")
        print(f"Position: {player.position or 'N/A'}")
        print(f"Jersey Number: {player.jersey_number or 'N/A'}")
        
        if player.team:
            print(f"\nTeam:")
            print(f"  ID: {player.team.id}")
            print(f"  Name: {player.team.name}")
        
        print(f"\nStatistics:")
        print(f"  Goals: {player.stats.goals}")
        print(f"  Assists: {player.stats.assists}")
        print(f"  Penalties: {player.stats.penalties}")
        print(f"  Games Played: {player.stats.games_played}")
        print(f"{'='*50}\n")


def main():
    """Main function to demonstrate the parser"""
    parser = BandyAPIParser()
    
    # Fetch and parse player information
    player_id = 439465
    print(f"Fetching player information for ID: {player_id}")
    
    player = parser.get_player_info(player_id, ttl=180)
    
    if player:
        parser.print_player_info(player)
        # Also print raw JSON for reference
        print("Raw JSON data available through get_player_info() method")
    else:
        print("Failed to fetch player information")


if __name__ == "__main__":
    main()