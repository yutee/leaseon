import requests
import pandas as pd
import numpy as np
import json
import time
from typing import Dict, List
import os

class FootballDataCollector:
    """
    Collects football data from API-Football (free tier)
    """
    
    def __init__(self, api_key: str = None):
        # self.api_key = os.environ.get("FOOTBALL_API_KEY")
        # if not self.api_key:
        #     raise ValueError("FOOTBALL_API_KEY environment variable not set.")
        self.api_key = api_key or "30ee08ffbcmshe2014047b3cf84fp105cf4jsnc025aa0ece07"  # Get from https://rapidapi.com/api-sports/api/api-football
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-rapidapi-host': 'v3.football.api-sports.io',
            'x-rapidapi-key': self.api_key
        }
        
        # Premier League Big 6 team IDs
        self.big6_teams = {
            'Manchester City': 50,
            'Arsenal': 42,
            'Liverpool': 40,
            'Chelsea': 49,
            'Manchester United': 33,
            'Tottenham': 47
        }
        
        # Premier League ID
        self.premier_league_id = 39
        self.current_season = 2024
    
    def get_team_squad(self, team_id: int) -> List[Dict]:
        """Get current squad for a team"""
        url = f"{self.base_url}/players/squads"
        params = {'team': team_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return data['response'][0]['players'] if data['response'] else []
            else:
                print(f"Error fetching squad for team {team_id}: {response.status_code}")
                return []
        except Exception as e:
            print(f"Exception fetching squad: {e}")
            return []
    
    def get_player_stats(self, player_id: int, season: int = 2024) -> Dict:
        """Get player statistics for a season"""
        url = f"{self.base_url}/players"
        params = {
            'id': player_id,
            'season': season,
            'league': self.premier_league_id
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return data['response'][0] if data['response'] else {}
            else:
                return {}
        except Exception as e:
            print(f"Exception fetching player stats: {e}")
            return {}
    
    def generate_mock_data(self) -> pd.DataFrame:
        """
        Generate mock football data for training
        (Use this if you don't have API access)
        """
        np.random.seed(42)
        
        # Sample player data
        positions = ['Goalkeeper', 'Defender', 'Midfielder', 'Attacker']
        clubs = list(self.big6_teams.keys())
        
        # Generate 500 mock transfer records
        data = []
        for i in range(500):
            # Player attributes
            age = np.random.randint(18, 35)
            market_value = np.random.randint(5, 100) * 1000000  # 5M to 100M
            goals = np.random.randint(0, 30) if np.random.choice([True, False], p=[0.6, 0.4]) else 0
            assists = np.random.randint(0, 20)
            minutes_played = np.random.randint(500, 3500)
            position = np.random.choice(positions)
            
            # Club attributes
            club_budget = np.random.randint(50, 200) * 1000000  # 50M to 200M
            club_league_position = np.random.randint(1, 20)
            club_champions_league = np.random.choice([0, 1], p=[0.7, 0.3])
            
            # Transfer features
            contract_years_left = np.random.randint(0, 5)
            player_wants_move = np.random.choice([0, 1], p=[0.7, 0.3])
            
            # Position need (club weakness in position)
            position_need = np.random.choice([0, 1, 2, 3])  # 0=no need, 3=urgent need
            
            # Calculate transfer probability (target variable)
            base_prob = 0.1
            
            # Age factor
            if 22 <= age <= 28:
                base_prob += 0.3
            elif age > 30:
                base_prob -= 0.2
                
            # Budget factor
            if market_value <= club_budget * 0.3:
                base_prob += 0.4
            elif market_value > club_budget * 0.5:
                base_prob -= 0.3
                
            # Performance factor
            if goals > 15 or assists > 10:
                base_prob += 0.2
                
            # Position need factor
            base_prob += position_need * 0.15
            
            # Contract situation
            if contract_years_left <= 1:
                base_prob += 0.25
                
            # Player desire
            if player_wants_move:
                base_prob += 0.2
                
            # Champions League factor
            if club_champions_league:
                base_prob += 0.1
                
            # Clamp probability between 0 and 1
            transfer_probability = max(0, min(1, base_prob + np.random.normal(0, 0.1)))
            
            # Create binary target (1 if transfer happens)
            transfer_happened = 1 if transfer_probability > 0.6 else 0
            
            data.append({
                'player_age': age,
                'market_value': market_value,
                'goals': goals,
                'assists': assists,
                'minutes_played': minutes_played,
                'position': position,
                'club_budget': club_budget,
                'club_league_position': club_league_position,
                'club_champions_league': club_champions_league,
                'contract_years_left': contract_years_left,
                'player_wants_move': player_wants_move,
                'position_need': position_need,
                'transfer_happened': transfer_happened,
                'transfer_probability': transfer_probability
            })
        
        return pd.DataFrame(data)
    
    def save_data(self, df: pd.DataFrame, filename: str = 'transfer_data.csv'):
        """Save data to CSV"""
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        
    def load_data(self, filename: str = 'transfer_data.csv') -> pd.DataFrame:
        """Load data from CSV"""
        if os.path.exists(filename):
            return pd.read_csv(filename)
        else:
            print(f"File {filename} not found. Generating mock data...")
            df = self.generate_mock_data()
            self.save_data(df, filename)
            return df

if __name__ == "__main__":
    collector = FootballDataCollector()
    
    # Generate and save mock data
    df = collector.generate_mock_data()
    collector.save_data(df)
    
    print("Sample data:")
    print(df.head())
    print(f"\nDataset shape: {df.shape}")
    print(f"Transfer rate: {df['transfer_happened'].mean():.2%}")