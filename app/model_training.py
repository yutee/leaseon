import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import json
from data_collection import FootballDataCollector

class TransferPredictor:
    """
    ML Model for predicting football transfers
    """
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2
        )
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        
        # Big 6 clubs info
        self.big6_clubs = {
            'Manchester City': {'budget': 180000000, 'cl_qualified': 1, 'league_pos': 1},
            'Arsenal': {'budget': 150000000, 'cl_qualified': 1, 'league_pos': 2},
            'Liverpool': {'budget': 140000000, 'cl_qualified': 1, 'league_pos': 3},
            'Chelsea': {'budget': 200000000, 'cl_qualified': 0, 'league_pos': 6},
            'Manchester United': {'budget': 160000000, 'cl_qualified': 0, 'league_pos': 8},
            'Tottenham': {'budget': 120000000, 'cl_qualified': 0, 'league_pos': 5}
        }
    
    def prepare_data(self, df: pd.DataFrame):
        """Prepare data for training"""
        # Create a copy
        data = df.copy()
        
        # Encode categorical variables
        categorical_cols = ['position']
        
        for col in categorical_cols:
            if col in data.columns:
                le = LabelEncoder()
                data[col] = le.fit_transform(data[col])
                self.label_encoders[col] = le
        
        # Select features
        feature_cols = [
            'player_age', 'market_value', 'goals', 'assists', 'minutes_played',
            'position', 'club_budget', 'club_league_position', 'club_champions_league',
            'contract_years_left', 'player_wants_move', 'position_need'
        ]
        
        # Filter existing columns
        feature_cols = [col for col in feature_cols if col in data.columns]
        self.feature_names = feature_cols
        
        X = data[feature_cols]
        y = data['transfer_happened'] if 'transfer_happened' in data.columns else None
        
        return X, y
    
    def train(self, df: pd.DataFrame):
        """Train the model"""
        print("Preparing data...")
        X, y = self.prepare_data(df)
        
        if y is None:
            raise ValueError("No target variable 'transfer_happened' found")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        print("Training model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Model Accuracy: {accuracy:.3f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 5 Most Important Features:")
        print(feature_importance.head())
        
        return accuracy
    
    def predict_transfer_probability(self, player_data: dict, club_name: str):
        """Predict transfer probability for a player to a specific club"""
        
        # Get club information
        club_info = self.big6_clubs.get(club_name, {
            'budget': 100000000,
            'cl_qualified': 0,
            'league_pos': 10
        })
        
        # Create input data
        input_data = {
            'player_age': player_data.get('age', 25),
            'market_value': player_data.get('market_value', 20000000),
            'goals': player_data.get('goals', 5),
            'assists': player_data.get('assists', 3),
            'minutes_played': player_data.get('minutes_played', 2000),
            'position': player_data.get('position', 'Midfielder'),
            'club_budget': club_info['budget'],
            'club_league_position': club_info['league_pos'],
            'club_champions_league': club_info['cl_qualified'],
            'contract_years_left': player_data.get('contract_years_left', 2),
            'player_wants_move': player_data.get('player_wants_move', 0),
            'position_need': player_data.get('position_need', 1)
        }
        
        # Convert to DataFrame
        input_df = pd.DataFrame([input_data])
        
        # Encode categorical variables
        for col, encoder in self.label_encoders.items():
            if col in input_df.columns:
                try:
                    input_df[col] = encoder.transform(input_df[col])
                except ValueError:
                    # Handle unknown categories
                    input_df[col] = 0
        
        # Select and order features
        X = input_df[self.feature_names]
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict probability
        probability = self.model.predict_proba(X_scaled)[0][1]  # Probability of transfer
        prediction = self.model.predict(X_scaled)[0]
        
        return {
            'transfer_probability': float(probability),
            'prediction': int(prediction),
            'confidence': 'High' if probability > 0.7 or probability < 0.3 else 'Medium'
        }
    
    def get_position_priorities(self, club_name: str):
        """Get position priorities for a club (mock implementation)"""
        # This would normally analyze current squad composition
        # For now, return mock priorities
        priorities = {
            'Manchester City': {'Attacker': 2, 'Midfielder': 1, 'Defender': 2, 'Goalkeeper': 0},
            'Arsenal': {'Attacker': 3, 'Midfielder': 2, 'Defender': 1, 'Goalkeeper': 1},
            'Liverpool': {'Attacker': 2, 'Midfielder': 3, 'Defender': 2, 'Goalkeeper': 0},
            'Chelsea': {'Attacker': 3, 'Midfielder': 2, 'Defender': 2, 'Goalkeeper': 1},
            'Manchester United': {'Attacker': 3, 'Midfielder': 2, 'Defender': 3, 'Goalkeeper': 0},
            'Tottenham': {'Attacker': 2, 'Midfielder': 1, 'Defender': 3, 'Goalkeeper': 1}
        }
        
        return priorities.get(club_name, {'Attacker': 2, 'Midfielder': 2, 'Defender': 2, 'Goalkeeper': 1})
    
    def save_model(self, path: str = 'models/'):
        """Save trained model and preprocessors"""
        import os
        os.makedirs(path, exist_ok=True)
        
        joblib.dump(self.model, f'{path}/transfer_model.pkl')
        joblib.dump(self.scaler, f'{path}/scaler.pkl')
        joblib.dump(self.label_encoders, f'{path}/label_encoders.pkl')
        
        # Save feature names and club info
        with open(f'{path}/model_config.json', 'w') as f:
            json.dump({
                'feature_names': self.feature_names,
                'big6_clubs': self.big6_clubs
            }, f, indent=2)
        
        print(f"Model saved to {path}")
    
    def load_model(self, path: str = 'models/'):
        """Load trained model and preprocessors"""
        self.model = joblib.load(f'{path}/transfer_model.pkl')
        self.scaler = joblib.load(f'{path}/scaler.pkl')
        self.label_encoders = joblib.load(f'{path}/label_encoders.pkl')
        
        with open(f'{path}/model_config.json', 'r') as f:
            config = json.load(f)
            self.feature_names = config['feature_names']
            self.big6_clubs = config['big6_clubs']
        
        print(f"Model loaded from {path}")

def main():
    """Main training function"""
    print("🏈 Football Transfer Predictor - Training")
    print("=" * 50)
    
    # Collect data
    collector = FootballDataCollector()
    df = collector.load_data()
    
    print(f"Loaded {len(df)} transfer records")
    
    # Initialize and train model
    predictor = TransferPredictor()
    accuracy = predictor.train(df)
    
    # Save model
    predictor.save_model()
    
    print(f"\n✅ Model training completed with {accuracy:.3f} accuracy")
    print("🔹 Model saved to 'models/' directory")
    
    # Test prediction
    print("\n🧪 Testing prediction...")
    test_player = {
        'age': 26,
        'market_value': 45000000,
        'goals': 18,
        'assists': 8,
        'minutes_played': 2800,
        'position': 'Attacker',
        'contract_years_left': 1,
        'player_wants_move': 1,
        'position_need': 3
    }
    
    result = predictor.predict_transfer_probability(test_player, 'Arsenal')
    print(f"Sample prediction for Arsenal: {result}")

if __name__ == "__main__":
    main()