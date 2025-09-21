from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import logging
from contextlib import asynccontextmanager
from model_training import TransferPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance
predictor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global predictor
    logger.info("Loading transfer prediction model...")
    
    try:
        predictor = TransferPredictor()
        
        # Check if model exists, if not train it
        model_path = 'models/'
        if not os.path.exists(f'{model_path}/transfer_model.pkl'):
            logger.info("No pre-trained model found. Training new model...")
            from data_collection import FootballDataCollector
            
            # Generate training data and train model
            collector = FootballDataCollector()
            df = collector.generate_mock_data()
            collector.save_data(df)
            
            predictor.train(df)
            predictor.save_model()
            logger.info("Model training completed and saved")
        else:
            predictor.load_model(model_path)
            logger.info("Pre-trained model loaded successfully")
            
    except Exception as e:
        logger.error(f"Failed to load/train model: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down transfer prediction service")

app = FastAPI(
    title="⚽ Football Transfer Predictor API",
    description="ML-powered API for predicting football transfers for Premier League Big 6 clubs",
    version="1.0.0",
    lifespan=lifespan
)

# Request/Response Models
class PlayerData(BaseModel):
    name: Optional[str] = "Unknown Player"
    age: int
    position: str  # Goalkeeper, Defender, Midfielder, Attacker
    market_value: int  # in euros
    goals: Optional[int] = 0
    assists: Optional[int] = 0
    minutes_played: Optional[int] = 1800
    contract_years_left: Optional[int] = 2
    player_wants_move: Optional[int] = 0  # 0 = no, 1 = yes
    position_need: Optional[int] = 1  # 0 = no need, 3 = urgent need

class TransferPredictionRequest(BaseModel):
    player: PlayerData
    target_club: str  # One of the Big 6 clubs

class TransferPredictionResponse(BaseModel):
    player_name: str
    target_club: str
    transfer_probability: float
    prediction: str  # "Likely" or "Unlikely"
    confidence: str  # "High", "Medium", "Low"
    reasoning: str
    market_fit: str
    position_priority: int

class ClubAnalysisResponse(BaseModel):
    club_name: str
    position_priorities: Dict[str, int]
    total_budget: int
    champions_league: bool
    recommendations: List[str]

class MultiClubRequest(BaseModel):
    player: PlayerData
    clubs: Optional[List[str]] = ["Manchester City", "Arsenal", "Liverpool", "Chelsea", "Manchester United", "Tottenham"]

class MultiClubResponse(BaseModel):
    player_name: str
    predictions: List[TransferPredictionResponse]
    best_fit: str
    summary: str

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": predictor is not None,
        "service": "Football Transfer Predictor"
    }

# Get available clubs
@app.get("/clubs")
async def get_clubs():
    """Get list of supported clubs"""
    if not predictor:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "supported_clubs": list(predictor.big6_clubs.keys()),
        "description": "Premier League Big 6 clubs supported by the API"
    }

# Club analysis endpoint
@app.get("/club/{club_name}/analysis", response_model=ClubAnalysisResponse)
async def analyze_club(club_name: str):
    """Get club analysis including position priorities and budget info"""
    if not predictor:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if club_name not in predictor.big6_clubs:
        raise HTTPException(status_code=400, detail=f"Club '{club_name}' not supported. Use one of: {list(predictor.big6_clubs.keys())}")
    
    club_info = predictor.big6_clubs[club_name]
    position_priorities = predictor.get_position_priorities(club_name)
    
    # Generate recommendations based on priorities
    recommendations = []
    for position, priority in position_priorities.items():
        if priority >= 2:
            recommendations.append(f"High priority: {position} - Priority level {priority}")
        elif priority == 1:
            recommendations.append(f"Medium priority: {position}")
    
    if not recommendations:
        recommendations = ["Squad well balanced - focus on quality upgrades"]
    
    return ClubAnalysisResponse(
        club_name=club_name,
        position_priorities=position_priorities,
        total_budget=club_info['budget'],
        champions_league=bool(club_info['cl_qualified']),
        recommendations=recommendations
    )

# Single transfer prediction
@app.post("/predict", response_model=TransferPredictionResponse)
async def predict_transfer(request: TransferPredictionRequest):
    """Predict transfer probability for a specific player-club combination"""
    if not predictor:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if request.target_club not in predictor.big6_clubs:
        raise HTTPException(status_code=400, detail=f"Club '{request.target_club}' not supported")
    
    try:
        # Convert player data to dict
        player_dict = {
            'age': request.player.age,
            'market_value': request.player.market_value,
            'goals': request.player.goals,
            'assists': request.player.assists,
            'minutes_played': request.player.minutes_played,
            'position': request.player.position,
            'contract_years_left': request.player.contract_years_left,
            'player_wants_move': request.player.player_wants_move,
            'position_need': request.player.position_need
        }
        
        # Get prediction
        result = predictor.predict_transfer_probability(player_dict, request.target_club)
        
        # Generate reasoning
        reasoning_parts = []
        
        # Age factor
        if 22 <= request.player.age <= 28:
            reasoning_parts.append("✅ Prime age range")
        elif request.player.age > 30:
            reasoning_parts.append("⚠️ Advanced age may reduce appeal")
        else:
            reasoning_parts.append("📈 Young with potential")
        
        # Performance factor
        if request.player.goals > 15 or request.player.assists > 10:
            reasoning_parts.append("⚽ Strong attacking output")
        
        # Contract situation
        if request.player.contract_years_left <= 1:
            reasoning_parts.append("📝 Contract situation favorable")
        
        # Budget fit
        club_budget = predictor.big6_clubs[request.target_club]['budget']
        if request.player.market_value <= club_budget * 0.3:
            market_fit = "Excellent fit"
            reasoning_parts.append("💰 Well within budget")
        elif request.player.market_value <= club_budget * 0.5:
            market_fit = "Good fit"
            reasoning_parts.append("💰 Reasonable price")
        else:
            market_fit = "Expensive"
            reasoning_parts.append("💰 High cost may be obstacle")
        
        # Position priority
        position_priorities = predictor.get_position_priorities(request.target_club)
        position_priority = position_priorities.get(request.player.position, 1)
        
        if position_priority >= 2:
            reasoning_parts.append(f"🎯 {request.player.position} is a priority position")
        
        reasoning = " | ".join(reasoning_parts)
        
        return TransferPredictionResponse(
            player_name=request.player.name,
            target_club=request.target_club,
            transfer_probability=result['transfer_probability'],
            prediction="Likely" if result['prediction'] == 1 else "Unlikely",
            confidence=result['confidence'],
            reasoning=reasoning,
            market_fit=market_fit,
            position_priority=position_priority
        )
        
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# Multi-club comparison
@app.post("/predict/multi-club", response_model=MultiClubResponse)
async def predict_multi_club(request: MultiClubRequest):
    """Compare transfer probability across multiple clubs"""
    if not predictor:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    predictions = []
    best_probability = 0
    best_club = ""
    
    for club in request.clubs:
        if club not in predictor.big6_clubs:
            continue
            
        try:
            # Create individual prediction request
            single_request = TransferPredictionRequest(
                player=request.player,
                target_club=club
            )
            
            # Get prediction (reuse the logic from predict_transfer)
            player_dict = {
                'age': request.player.age,
                'market_value': request.player.market_value,
                'goals': request.player.goals,
                'assists': request.player.assists,
                'minutes_played': request.player.minutes_played,
                'position': request.player.position,
                'contract_years_left': request.player.contract_years_left,
                'player_wants_move': request.player.player_wants_move,
                'position_need': request.player.position_need
            }
            
            result = predictor.predict_transfer_probability(player_dict, club)
            
            # Track best option
            if result['transfer_probability'] > best_probability:
                best_probability = result['transfer_probability']
                best_club = club
            
            # Create simplified response for multi-club
            prediction_response = TransferPredictionResponse(
                player_name=request.player.name,
                target_club=club,
                transfer_probability=result['transfer_probability'],
                prediction="Likely" if result['prediction'] == 1 else "Unlikely",
                confidence=result['confidence'],
                reasoning=f"Probability: {result['transfer_probability']:.2%}",
                market_fit="TBD",
                position_priority=predictor.get_position_priorities(club).get(request.player.position, 1)
            )
            
            predictions.append(prediction_response)
            
        except Exception as e:
            logger.warning(f"Error predicting for {club}: {e}")
            continue
    
    # Sort by probability
    predictions.sort(key=lambda x: x.transfer_probability, reverse=True)
    
    # Generate summary
    if best_probability > 0.7:
        summary = f"🎯 Excellent fit for {best_club} ({best_probability:.1%} probability)"
    elif best_probability > 0.5:
        summary = f"✅ Good options available, best fit: {best_club} ({best_probability:.1%})"
    else:
        summary = f"⚠️ Limited opportunities, best option: {best_club} ({best_probability:.1%})"
    
    return MultiClubResponse(
        player_name=request.player.name,
        predictions=predictions,
        best_fit=best_club,
        summary=summary
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "⚽ Football Transfer Predictor API",
        "version": "1.0.0",
        "description": "ML-powered transfer predictions for Premier League Big 6 clubs",
        "endpoints": {
            "GET /health": "Health check",
            "GET /clubs": "Get supported clubs",
            "GET /club/{club_name}/analysis": "Club analysis and priorities",
            "POST /predict": "Single transfer prediction",
            "POST /predict/multi-club": "Multi-club comparison",
            "GET /docs": "Interactive API documentation"
        },
        "supported_clubs": [
            "Manchester City", "Arsenal", "Liverpool", 
            "Chelsea", "Manchester United", "Tottenham"
        ],
        "example_usage": {
            "predict_endpoint": "/predict",
            "sample_request": {
                "player": {
                    "name": "Sample Player",
                    "age": 26,
                    "position": "Attacker",
                    "market_value": 45000000,
                    "goals": 18,
                    "assists": 8
                },
                "target_club": "Arsenal"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)