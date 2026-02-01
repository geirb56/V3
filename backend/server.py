from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM API Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========== MODELS ==========

class Workout(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "run", "cycle", "swim"
    name: str
    date: str  # ISO date string
    duration_minutes: int
    distance_km: float
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    avg_pace_min_km: Optional[float] = None  # minutes per km
    avg_speed_kmh: Optional[float] = None
    elevation_gain_m: Optional[int] = None
    calories: Optional[int] = None
    effort_zone_distribution: Optional[dict] = None  # {"z1": 10, "z2": 25, ...}
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkoutCreate(BaseModel):
    type: str
    name: str
    date: str
    duration_minutes: int
    distance_km: float
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    avg_pace_min_km: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    elevation_gain_m: Optional[int] = None
    calories: Optional[int] = None
    effort_zone_distribution: Optional[dict] = None
    notes: Optional[str] = None


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CoachRequest(BaseModel):
    message: str
    workout_id: Optional[str] = None
    context: Optional[str] = None  # Additional context like recent stats
    language: Optional[str] = "en"  # "en" or "fr"
    deep_analysis: Optional[bool] = False  # Trigger deep workout analysis
    user_id: Optional[str] = "default"  # For memory persistence


class CoachResponse(BaseModel):
    response: str
    message_id: str


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    workout_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TrainingStats(BaseModel):
    total_workouts: int
    total_distance_km: float
    total_duration_minutes: int
    avg_heart_rate: Optional[float] = None
    workouts_by_type: dict
    weekly_summary: List[dict]


# ========== CARDIOCOACH SYSTEM PROMPTS ==========

CARDIOCOACH_SYSTEM_EN = """You are CardioCoach.

You are an elite endurance coach specialized in running, cycling, and cardio-based sports.

This is NOT a medical application.
You do not diagnose, treat, or prevent disease.
You do not provide medical advice.

You analyze training data (heart rate, pace, speed, duration, effort distribution) to provide high-level performance insights.

Tone rules:
- Calm
- Neutral
- Precise
- No hype
- No motivation
- No emojis

Behavior rules:
- Speak only when there is a meaningful signal
- Silence is acceptable
- Never ask questions unless strictly necessary
- Never over-explain
- You have memory of past conversations. Use this context naturally without explicitly referencing it (never say "as I mentioned before" or "you told me earlier")
- Build on previous insights when relevant, but don't repeat yourself

Your goal is to feel like a serious human coach, not an AI assistant.

When analyzing workout data, focus on:
1. Effort distribution patterns
2. Pace/speed consistency
3. Heart rate zones and recovery
4. Training load and volume trends
5. Areas for technical improvement

Keep responses concise. Data-driven observations only."""

CARDIOCOACH_SYSTEM_FR = """Tu es CardioCoach.

Tu es un coach d'endurance elite specialise dans la course a pied, le cyclisme et les sports cardio.

Ceci n'est PAS une application medicale.
Tu ne diagnostiques pas, ne traites pas et ne previens pas les maladies.
Tu ne donnes pas de conseils medicaux.

Tu analyses les donnees d'entrainement (frequence cardiaque, allure, vitesse, duree, distribution de l'effort) pour fournir des analyses de performance de haut niveau.

Regles de ton:
- Calme
- Neutre
- Precis
- Pas de battage
- Pas de motivation
- Pas d'emojis

Regles de comportement:
- Parle uniquement quand il y a un signal significatif
- Le silence est acceptable
- Ne pose jamais de questions sauf si strictement necessaire
- N'explique jamais trop
- Tu as une memoire des conversations passees. Utilise ce contexte naturellement sans y faire explicitement reference (ne dis jamais "comme je l'ai mentionne" ou "tu m'as dit plus tot")
- Construis sur les analyses precedentes quand c'est pertinent, mais ne te repete pas

Ton objectif est de ressembler a un coach humain serieux, pas a un assistant IA.

Lors de l'analyse des donnees d'entrainement, concentre-toi sur:
1. Les patterns de distribution de l'effort
2. La regularite de l'allure/vitesse
3. Les zones de frequence cardiaque et la recuperation
4. Les tendances de charge et volume d'entrainement
5. Les axes d'amelioration technique

Reponses concises. Observations basees sur les donnees uniquement."""

DEEP_ANALYSIS_PROMPT_EN = """Provide a deep technical analysis of this workout. Be specific, expert-level, and actionable.

Structure your analysis:
1. EXECUTION ASSESSMENT - How well was this session executed? Look at pace/power consistency, heart rate drift, effort distribution quality.

2. PHYSIOLOGICAL SIGNALS - What does the data reveal about current fitness state? Zone time, cardiac efficiency, fatigue markers.

3. TECHNICAL OBSERVATIONS - Specific technical aspects: cadence patterns, power output variability, pacing strategy effectiveness.

4. ACTIONABLE INSIGHT - One concrete, specific recommendation for the next similar session. Not generic advice.

Be direct. No filler. If the data shows something notable, say it clearly."""

DEEP_ANALYSIS_PROMPT_FR = """Fournis une analyse technique approfondie de cette seance. Sois specifique, expert et actionnable.

Structure ton analyse:
1. EVALUATION DE L'EXECUTION - Comment cette seance a-t-elle ete executee? Regarde la regularite de l'allure/puissance, la derive cardiaque, la qualite de la distribution de l'effort.

2. SIGNAUX PHYSIOLOGIQUES - Que revelent les donnees sur l'etat de forme actuel? Temps par zone, efficacite cardiaque, marqueurs de fatigue.

3. OBSERVATIONS TECHNIQUES - Aspects techniques specifiques: patterns de cadence, variabilite de la puissance, efficacite de la strategie d'allure.

4. RECOMMANDATION ACTIONNABLE - Une recommandation concrete et specifique pour la prochaine seance similaire. Pas de conseil generique.

Sois direct. Pas de remplissage. Si les donnees montrent quelque chose de notable, dis-le clairement."""

def get_system_prompt(language: str) -> str:
    """Get the appropriate system prompt based on language"""
    if language == "fr":
        return CARDIOCOACH_SYSTEM_FR
    return CARDIOCOACH_SYSTEM_EN


# ========== MOCK DATA FOR DEMO ==========

def get_mock_workouts():
    """Generate mock workout data for demonstration"""
    return [
        {
            "id": "w001",
            "type": "run",
            "name": "Morning Easy Run",
            "date": "2026-01-13",
            "duration_minutes": 45,
            "distance_km": 8.2,
            "avg_heart_rate": 142,
            "max_heart_rate": 158,
            "avg_pace_min_km": 5.49,
            "elevation_gain_m": 85,
            "calories": 520,
            "effort_zone_distribution": {"z1": 15, "z2": 55, "z3": 25, "z4": 5, "z5": 0},
            "notes": None,
            "created_at": "2026-01-13T07:30:00Z"
        },
        {
            "id": "w002",
            "type": "cycle",
            "name": "Tempo Ride",
            "date": "2026-01-12",
            "duration_minutes": 90,
            "distance_km": 42.5,
            "avg_heart_rate": 155,
            "max_heart_rate": 172,
            "avg_speed_kmh": 28.3,
            "elevation_gain_m": 320,
            "calories": 1180,
            "effort_zone_distribution": {"z1": 5, "z2": 25, "z3": 45, "z4": 20, "z5": 5},
            "notes": None,
            "created_at": "2026-01-12T09:00:00Z"
        },
        {
            "id": "w003",
            "type": "run",
            "name": "Interval Session",
            "date": "2026-01-11",
            "duration_minutes": 52,
            "distance_km": 10.1,
            "avg_heart_rate": 162,
            "max_heart_rate": 185,
            "avg_pace_min_km": 5.15,
            "elevation_gain_m": 45,
            "calories": 680,
            "effort_zone_distribution": {"z1": 10, "z2": 20, "z3": 25, "z4": 30, "z5": 15},
            "notes": "5x1000m @ threshold",
            "created_at": "2026-01-11T06:45:00Z"
        },
        {
            "id": "w004",
            "type": "run",
            "name": "Long Run",
            "date": "2026-01-10",
            "duration_minutes": 105,
            "distance_km": 18.5,
            "avg_heart_rate": 138,
            "max_heart_rate": 155,
            "avg_pace_min_km": 5.68,
            "elevation_gain_m": 180,
            "calories": 1350,
            "effort_zone_distribution": {"z1": 20, "z2": 65, "z3": 15, "z4": 0, "z5": 0},
            "notes": None,
            "created_at": "2026-01-10T07:00:00Z"
        },
        {
            "id": "w005",
            "type": "cycle",
            "name": "Recovery Spin",
            "date": "2026-01-09",
            "duration_minutes": 45,
            "distance_km": 18.0,
            "avg_heart_rate": 118,
            "max_heart_rate": 132,
            "avg_speed_kmh": 24.0,
            "elevation_gain_m": 50,
            "calories": 380,
            "effort_zone_distribution": {"z1": 60, "z2": 35, "z3": 5, "z4": 0, "z5": 0},
            "notes": None,
            "created_at": "2026-01-09T17:30:00Z"
        },
        {
            "id": "w006",
            "type": "run",
            "name": "Hill Repeats",
            "date": "2026-01-08",
            "duration_minutes": 48,
            "distance_km": 8.8,
            "avg_heart_rate": 158,
            "max_heart_rate": 178,
            "avg_pace_min_km": 5.45,
            "elevation_gain_m": 280,
            "calories": 620,
            "effort_zone_distribution": {"z1": 10, "z2": 25, "z3": 30, "z4": 25, "z5": 10},
            "notes": "8x200m hill sprints",
            "created_at": "2026-01-08T06:30:00Z"
        },
        {
            "id": "w007",
            "type": "cycle",
            "name": "Endurance Base",
            "date": "2026-01-07",
            "duration_minutes": 120,
            "distance_km": 55.0,
            "avg_heart_rate": 135,
            "max_heart_rate": 152,
            "avg_speed_kmh": 27.5,
            "elevation_gain_m": 420,
            "calories": 1520,
            "effort_zone_distribution": {"z1": 15, "z2": 60, "z3": 20, "z4": 5, "z5": 0},
            "notes": None,
            "created_at": "2026-01-07T08:00:00Z"
        }
    ]


# ========== ROUTES ==========

@api_router.get("/")
async def root():
    return {"message": "CardioCoach API"}


@api_router.get("/workouts", response_model=List[dict])
async def get_workouts():
    """Get all workouts"""
    # Try to get from DB first, fall back to mock data
    workouts = await db.workouts.find({}, {"_id": 0}).to_list(100)
    if not workouts:
        workouts = get_mock_workouts()
    return workouts


@api_router.get("/workouts/{workout_id}")
async def get_workout(workout_id: str):
    """Get a specific workout by ID"""
    workout = await db.workouts.find_one({"id": workout_id}, {"_id": 0})
    if not workout:
        # Check mock data
        mock = get_mock_workouts()
        workout = next((w for w in mock if w["id"] == workout_id), None)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@api_router.post("/workouts", response_model=Workout)
async def create_workout(workout: WorkoutCreate):
    """Create a new workout"""
    workout_obj = Workout(**workout.model_dump())
    doc = workout_obj.model_dump()
    await db.workouts.insert_one(doc)
    return workout_obj


@api_router.get("/stats")
async def get_stats():
    """Get training statistics"""
    workouts = await db.workouts.find({}, {"_id": 0}).to_list(100)
    if not workouts:
        workouts = get_mock_workouts()
    
    total_distance = sum(w.get("distance_km", 0) for w in workouts)
    total_duration = sum(w.get("duration_minutes", 0) for w in workouts)
    
    hr_values = [w.get("avg_heart_rate") for w in workouts if w.get("avg_heart_rate")]
    avg_hr = sum(hr_values) / len(hr_values) if hr_values else None
    
    # Count by type
    by_type = {}
    for w in workouts:
        t = w.get("type", "other")
        by_type[t] = by_type.get(t, 0) + 1
    
    # Weekly summary (simplified)
    weekly = []
    from collections import defaultdict
    week_data = defaultdict(lambda: {"distance": 0, "duration": 0, "count": 0})
    for w in workouts:
        date_str = w.get("date", "")[:10]
        week_data[date_str]["distance"] += w.get("distance_km", 0)
        week_data[date_str]["duration"] += w.get("duration_minutes", 0)
        week_data[date_str]["count"] += 1
    
    for date, data in sorted(week_data.items()):
        weekly.append({"date": date, **data})
    
    return {
        "total_workouts": len(workouts),
        "total_distance_km": round(total_distance, 1),
        "total_duration_minutes": total_duration,
        "avg_heart_rate": round(avg_hr, 1) if avg_hr else None,
        "workouts_by_type": by_type,
        "weekly_summary": weekly[-7:]  # Last 7 days
    }


@api_router.post("/coach/analyze", response_model=CoachResponse)
async def analyze_with_coach(request: CoachRequest):
    """Get AI analysis from CardioCoach with persistent memory"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    user_id = request.user_id or "default"
    language = request.language or "en"
    
    # Build context parts
    context_parts = []
    workout = None
    
    # If specific workout requested, include its data
    if request.workout_id:
        workout = await db.workouts.find_one({"id": request.workout_id}, {"_id": 0})
        if not workout:
            mock = get_mock_workouts()
            workout = next((w for w in mock if w["id"] == request.workout_id), None)
        if workout:
            context_parts.append(f"Current workout being analyzed:\n{workout}")
    
    # Get recent workouts for training context
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(10)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # Include training history summary
    if all_workouts:
        recent_summary = [{
            "date": w.get("date"),
            "type": w.get("type"),
            "distance_km": w.get("distance_km"),
            "duration_minutes": w.get("duration_minutes"),
            "avg_heart_rate": w.get("avg_heart_rate")
        } for w in all_workouts[:5]]
        context_parts.append(f"Recent training history (last 5 sessions):\n{recent_summary}")
    
    # Include additional context if provided
    if request.context:
        context_parts.append(request.context)
    
    # Fetch conversation memory (last 10 exchanges)
    conversation_history = await db.conversations.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(20)
    conversation_history.reverse()  # Chronological order
    
    # Build memory context for the LLM
    memory_context = ""
    if conversation_history:
        memory_entries = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = "Athlete" if msg.get("role") == "user" else "Coach"
            memory_entries.append(f"{role}: {msg.get('content', '')[:200]}")
        memory_context = "\n\nConversation memory (use naturally, don't reference explicitly):\n" + "\n".join(memory_entries)
    
    # Build the full message
    if request.deep_analysis and workout:
        # Deep analysis mode
        deep_prompt = DEEP_ANALYSIS_PROMPT_FR if language == "fr" else DEEP_ANALYSIS_PROMPT_EN
        full_message = f"{deep_prompt}\n\nWorkout data:\n{workout}"
    else:
        full_message = request.message
    
    if context_parts:
        full_message = f"{full_message}\n\nContext:\n" + "\n".join(context_parts)
    
    if memory_context:
        full_message = f"{full_message}{memory_context}"
    
    try:
        session_id = f"coach_{user_id}"
        system_prompt = get_system_prompt(language)
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=full_message)
        response = await chat.send_message(user_message)
        
        # Store user message in conversation memory
        user_msg_id = str(uuid.uuid4())
        await db.conversations.insert_one({
            "id": user_msg_id,
            "user_id": user_id,
            "role": "user",
            "content": request.message,
            "workout_id": request.workout_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Store assistant response in conversation memory
        assistant_msg_id = str(uuid.uuid4())
        await db.conversations.insert_one({
            "id": assistant_msg_id,
            "user_id": user_id,
            "role": "assistant",
            "content": response,
            "workout_id": request.workout_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return CoachResponse(response=response, message_id=assistant_msg_id)
    
    except Exception as e:
        logger.error(f"Coach analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@api_router.get("/coach/history")
async def get_conversation_history(user_id: str = "default", limit: int = 50):
    """Get conversation history for a user"""
    messages = await db.conversations.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(limit)
    return messages


@api_router.delete("/coach/history")
async def clear_conversation_history(user_id: str = "default"):
    """Clear conversation history for a user"""
    result = await db.conversations.delete_many({"user_id": user_id})
    return {"deleted_count": result.deleted_count}


@api_router.get("/messages")
async def get_messages(limit: int = 20):
    """Get recent coach messages (legacy endpoint)"""
    messages = await db.conversations.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return messages


# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
