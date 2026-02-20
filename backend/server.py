from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import random
import secrets
import hashlib
import base64
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta

# Import the analysis engine (NO LLM dependencies)
from analysis_engine import (
    generate_session_analysis,
    generate_weekly_review,
    generate_dashboard_insight,
    calculate_intensity_level,
    format_duration,
    format_pace
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Garmin OAuth Configuration (placeholder - replace with real credentials)
GARMIN_CLIENT_ID = os.environ.get('GARMIN_CLIENT_ID', '')
GARMIN_CLIENT_SECRET = os.environ.get('GARMIN_CLIENT_SECRET', '')
GARMIN_REDIRECT_URI = os.environ.get('GARMIN_REDIRECT_URI', '')

# Strava OAuth Configuration
STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID', '')
STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET', '')
STRAVA_REDIRECT_URI = os.environ.get('STRAVA_REDIRECT_URI', '')

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

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
    data_source: Optional[str] = "manual"  # "manual", "garmin", etc.
    garmin_activity_id: Optional[str] = None  # For Garmin workouts
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
    data_source: Optional[str] = "manual"
    garmin_activity_id: Optional[str] = None


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


class GuidanceRequest(BaseModel):
    language: Optional[str] = "en"
    user_id: Optional[str] = "default"


class GuidanceResponse(BaseModel):
    status: str  # "maintain", "adjust", "hold_steady"
    guidance: str
    generated_at: str


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


# ========== GARMIN INTEGRATION MODELS ==========

class GarminConnectionStatus(BaseModel):
    connected: bool
    last_sync: Optional[str] = None
    workout_count: int = 0


class GarminSyncResult(BaseModel):
    success: bool
    synced_count: int
    message: str


# Temporary storage for PKCE pairs (in production, use Redis or DB)
pkce_store: Dict[str, str] = {}


# ========== GARMIN OAUTH HELPERS ==========

def generate_pkce_pair() -> tuple:
    """Generate PKCE code verifier and code challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


def get_garmin_auth_url(code_challenge: str, state: str) -> str:
    """Generate Garmin Connect authorization URL"""
    params = {
        "client_id": GARMIN_CLIENT_ID,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "redirect_uri": GARMIN_REDIRECT_URI,
        "state": state,
        "scope": "activity_export"
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://connect.garmin.com/oauthConfirm?{query}"


async def exchange_garmin_code(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://connectapi.garmin.com/oauth-service/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": GARMIN_CLIENT_ID,
                "client_secret": GARMIN_CLIENT_SECRET,
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": GARMIN_REDIRECT_URI
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()


async def fetch_garmin_activities(access_token: str, start_date: str = None) -> list:
    """Fetch activities from Garmin Connect API"""
    async with httpx.AsyncClient() as client:
        params = {"limit": 100}
        if start_date:
            params["start"] = start_date
        
        response = await client.get(
            "https://apis.garmin.com/wellness-api/rest/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        response.raise_for_status()
        return response.json()


def convert_garmin_to_workout(garmin_activity: dict, user_id: str = "default") -> dict:
    """Convert Garmin activity to CardioCoach workout format"""
    # Map Garmin activity types to our types
    activity_type_map = {
        "running": "run",
        "cycling": "cycle",
        "indoor_cycling": "cycle",
        "trail_running": "run",
        "treadmill_running": "run",
        "virtual_ride": "cycle",
        "road_biking": "cycle",
        "mountain_biking": "cycle",
    }
    
    garmin_type = garmin_activity.get("activityType", "").lower()
    workout_type = activity_type_map.get(garmin_type, None)
    
    # Only import running and cycling
    if not workout_type:
        return None
    
    # Extract metrics with graceful fallback for missing data
    duration_seconds = garmin_activity.get("duration", 0)
    distance_meters = garmin_activity.get("distance", 0)
    avg_hr = garmin_activity.get("averageHR")
    max_hr = garmin_activity.get("maxHR")
    calories = garmin_activity.get("calories")
    elevation = garmin_activity.get("elevationGain")
    
    # Calculate pace/speed
    avg_pace = None
    avg_speed = None
    if distance_meters and duration_seconds:
        if workout_type == "run":
            # Pace in min/km
            avg_pace = (duration_seconds / 60) / (distance_meters / 1000) if distance_meters > 0 else None
        else:
            # Speed in km/h
            avg_speed = (distance_meters / 1000) / (duration_seconds / 3600) if duration_seconds > 0 else None
    
    # Extract heart rate zones if available
    hr_zones = garmin_activity.get("heartRateZones")
    effort_distribution = None
    if hr_zones and isinstance(hr_zones, list) and len(hr_zones) >= 5:
        total_time = sum(z.get("secsInZone", 0) for z in hr_zones[:5])
        if total_time > 0:
            effort_distribution = {
                f"z{i+1}": round((hr_zones[i].get("secsInZone", 0) / total_time) * 100)
                for i in range(5)
            }
    
    # Build workout object
    start_time = garmin_activity.get("startTimeLocal") or garmin_activity.get("startTimeGMT")
    if start_time:
        try:
            if isinstance(start_time, (int, float)):
                date_obj = datetime.fromtimestamp(start_time / 1000, tz=timezone.utc)
            else:
                date_obj = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
        except:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    workout = {
        "id": f"garmin_{garmin_activity.get('activityId', uuid.uuid4())}",
        "type": workout_type,
        "name": garmin_activity.get("activityName", f"{workout_type.title()} Workout"),
        "date": date_str,
        "duration_minutes": round(duration_seconds / 60) if duration_seconds else 0,
        "distance_km": round(distance_meters / 1000, 2) if distance_meters else 0,
        "data_source": "garmin",
        "garmin_activity_id": str(garmin_activity.get("activityId")),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add optional fields only if present (graceful handling)
    if avg_hr:
        workout["avg_heart_rate"] = int(avg_hr)
    if max_hr:
        workout["max_heart_rate"] = int(max_hr)
    if avg_pace:
        workout["avg_pace_min_km"] = round(avg_pace, 2)
    if avg_speed:
        workout["avg_speed_kmh"] = round(avg_speed, 1)
    if calories:
        workout["calories"] = int(calories)
    if elevation:
        workout["elevation_gain_m"] = int(elevation)
    if effort_distribution:
        workout["effort_zone_distribution"] = effort_distribution
    
    return workout


# ========== STRAVA INTEGRATION HELPERS ==========

async def exchange_strava_code(code: str) -> dict:
    """Exchange authorization code for Strava access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/api/v3/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code"
            }
        )
        response.raise_for_status()
        return response.json()


async def refresh_strava_token(refresh_token: str) -> dict:
    """Refresh Strava access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/api/v3/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )
        response.raise_for_status()
        return response.json()


async def fetch_strava_activities(access_token: str, per_page: int = 100, max_pages: int = 3) -> list:
    """Fetch activities from Strava API (up to max_pages * per_page activities)"""
    all_activities = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            response = await client.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"per_page": per_page, "page": page}
            )
            response.raise_for_status()
            activities = response.json()
            
            if not activities:
                break  # No more activities
            
            all_activities.extend(activities)
            
            if len(activities) < per_page:
                break  # Last page
    
    logger.info(f"Fetched {len(all_activities)} activities from Strava")
    return all_activities


async def fetch_strava_activity_streams(access_token: str, activity_id: str) -> dict:
    """Fetch detailed streams (HR, pace, cadence) for a specific activity"""
    streams_data = {}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch HR, velocity, cadence, altitude streams
            response = await client.get(
                f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "keys": "heartrate,velocity_smooth,cadence,altitude,time",
                    "key_by_type": "true"
                }
            )
            
            if response.status_code == 200:
                streams = response.json()
                streams_data = streams
            else:
                logger.warning(f"Failed to fetch streams for activity {activity_id}: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error fetching streams for activity {activity_id}: {e}")
    
    return streams_data


async def fetch_strava_activity_zones(access_token: str, activity_id: str) -> dict:
    """Fetch heart rate zones distribution for a specific activity"""
    zones_data = {}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://www.strava.com/api/v3/activities/{activity_id}/zones",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                zones = response.json()
                zones_data = zones
            else:
                logger.warning(f"Failed to fetch zones for activity {activity_id}: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error fetching zones for activity {activity_id}: {e}")
    
    return zones_data


def calculate_hr_zones_from_stream(hr_stream: list, max_hr: int = None) -> dict:
    """Calculate time spent in each HR zone from stream data"""
    if not hr_stream or not max_hr:
        return None
    
    # Standard 5-zone model based on % of max HR
    # Z1: 50-60%, Z2: 60-70%, Z3: 70-80%, Z4: 80-90%, Z5: 90-100%
    zone_thresholds = [
        (0.50, 0.60, "z1"),
        (0.60, 0.70, "z2"),
        (0.70, 0.80, "z3"),
        (0.80, 0.90, "z4"),
        (0.90, 1.00, "z5"),
    ]
    
    zone_counts = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
    total_points = len(hr_stream)
    
    for hr in hr_stream:
        if hr is None:
            continue
        hr_pct = hr / max_hr
        
        for low, high, zone in zone_thresholds:
            if low <= hr_pct < high:
                zone_counts[zone] += 1
                break
        else:
            # Above 100% max HR
            if hr_pct >= 1.0:
                zone_counts["z5"] += 1
    
    # Convert to percentages
    if total_points > 0:
        zone_distribution = {
            zone: round((count / total_points) * 100)
            for zone, count in zone_counts.items()
        }
    else:
        zone_distribution = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
    
    return zone_distribution


def calculate_pace_stats_from_stream(velocity_stream: list, time_stream: list = None) -> dict:
    """Calculate detailed pace statistics from velocity stream (for running)"""
    if not velocity_stream:
        return None
    
    # Filter out zero/null values
    valid_velocities = [v for v in velocity_stream if v and v > 0]
    
    if not valid_velocities:
        return None
    
    # Convert m/s to min/km
    def ms_to_pace(v):
        if v <= 0:
            return None
        km_per_sec = v / 1000
        if km_per_sec <= 0:
            return None
        return 1 / (km_per_sec * 60)  # min/km
    
    paces = [ms_to_pace(v) for v in valid_velocities if ms_to_pace(v)]
    
    if not paces:
        return None
    
    avg_pace = sum(paces) / len(paces)
    min_pace = min(paces)  # Fastest
    max_pace = max(paces)  # Slowest
    
    # Calculate pace variability (standard deviation)
    variance = sum((p - avg_pace) ** 2 for p in paces) / len(paces)
    std_dev = variance ** 0.5
    
    return {
        "avg_pace_min_km": round(avg_pace, 2),
        "best_pace_min_km": round(min_pace, 2),
        "slowest_pace_min_km": round(max_pace, 2),
        "pace_variability": round(std_dev, 2)
    }


def convert_strava_to_workout(strava_activity: dict, streams_data: dict = None, zones_data: dict = None) -> dict:
    """Convert Strava activity to CardioCoach workout format with detailed HR and pace data"""
    # Map Strava activity types to our types
    activity_type_map = {
        "run": "run",
        "ride": "cycle",
        "virtualrun": "run",
        "virtualride": "cycle",
        "trailrun": "run",
        "mountainbikeride": "cycle",
        "gravelride": "cycle",
        "ebikeride": "cycle",
    }
    
    strava_type = strava_activity.get("type", "").lower()
    workout_type = activity_type_map.get(strava_type, None)
    
    # Only import running and cycling
    if not workout_type:
        return None
    
    # Extract metrics with graceful fallback for missing data
    elapsed_time = strava_activity.get("elapsed_time", 0)  # in seconds
    moving_time = strava_activity.get("moving_time", elapsed_time)  # in seconds
    distance = strava_activity.get("distance", 0)  # in meters
    avg_hr = strava_activity.get("average_heartrate")
    max_hr = strava_activity.get("max_heartrate")
    elevation = strava_activity.get("total_elevation_gain")
    calories = strava_activity.get("calories")
    avg_speed = strava_activity.get("average_speed", 0)  # in m/s
    max_speed = strava_activity.get("max_speed", 0)  # in m/s
    avg_cadence = strava_activity.get("average_cadence")
    
    # Calculate pace (for runs) or speed (for rides)
    avg_pace_min_km = None
    best_pace_min_km = None
    avg_speed_kmh = None
    max_speed_kmh = None
    
    if avg_speed and avg_speed > 0:
        if workout_type == "run":
            # Convert m/s to min/km
            speed_km_per_min = (avg_speed * 60) / 1000
            if speed_km_per_min > 0:
                avg_pace_min_km = round(1 / speed_km_per_min, 2)
            # Best pace from max speed
            if max_speed and max_speed > 0:
                max_speed_km_per_min = (max_speed * 60) / 1000
                if max_speed_km_per_min > 0:
                    best_pace_min_km = round(1 / max_speed_km_per_min, 2)
        else:
            # Convert m/s to km/h
            avg_speed_kmh = round(avg_speed * 3.6, 1)
            if max_speed:
                max_speed_kmh = round(max_speed * 3.6, 1)
    
    # Parse start time
    start_date = strava_activity.get("start_date_local") or strava_activity.get("start_date")
    if start_date:
        try:
            date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
        except:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Build workout object
    workout = {
        "id": f"strava_{strava_activity.get('id', uuid.uuid4())}",
        "type": workout_type,
        "name": strava_activity.get("name", f"{workout_type.title()} Workout"),
        "date": date_str,
        "duration_minutes": round(elapsed_time / 60) if elapsed_time else 0,
        "moving_time_minutes": round(moving_time / 60) if moving_time else 0,
        "distance_km": round(distance / 1000, 2) if distance else 0,
        "data_source": "strava",
        "strava_activity_id": str(strava_activity.get("id")),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Heart rate data
    if avg_hr:
        workout["avg_heart_rate"] = int(avg_hr)
    if max_hr:
        workout["max_heart_rate"] = int(max_hr)
    
    # Calculate HR zones from streams if available
    hr_zones = None
    if streams_data and "heartrate" in streams_data and max_hr:
        hr_stream = streams_data["heartrate"].get("data", [])
        if hr_stream:
            hr_zones = calculate_hr_zones_from_stream(hr_stream, int(max_hr))
    
    # Or use Strava's zone data if available
    if not hr_zones and zones_data:
        for zone_info in zones_data:
            if zone_info.get("type") == "heartrate":
                distribution_buckets = zone_info.get("distribution_buckets", [])
                if distribution_buckets:
                    total_time = sum(b.get("time", 0) for b in distribution_buckets)
                    if total_time > 0:
                        hr_zones = {}
                        for i, bucket in enumerate(distribution_buckets[:5]):
                            zone_key = f"z{i+1}"
                            hr_zones[zone_key] = round((bucket.get("time", 0) / total_time) * 100)
    
    if hr_zones:
        workout["effort_zone_distribution"] = hr_zones
    
    # Pace data (running)
    if workout_type == "run":
        if avg_pace_min_km:
            workout["avg_pace_min_km"] = avg_pace_min_km
        if best_pace_min_km:
            workout["best_pace_min_km"] = best_pace_min_km
        
        # Detailed pace stats from streams
        if streams_data and "velocity_smooth" in streams_data:
            velocity_stream = streams_data["velocity_smooth"].get("data", [])
            pace_stats = calculate_pace_stats_from_stream(velocity_stream)
            if pace_stats:
                workout["pace_stats"] = pace_stats
        
        # Cadence (steps per minute, Strava gives half - one foot)
        if avg_cadence:
            workout["avg_cadence_spm"] = int(avg_cadence * 2)  # Convert to full steps
    
    # Speed data (cycling)
    if workout_type == "cycle":
        if avg_speed_kmh:
            workout["avg_speed_kmh"] = avg_speed_kmh
        if max_speed_kmh:
            workout["max_speed_kmh"] = max_speed_kmh
        if avg_cadence:
            workout["avg_cadence_rpm"] = int(avg_cadence)
    
    # Elevation and calories
    if calories:
        workout["calories"] = int(calories)
    if elevation:
        workout["elevation_gain_m"] = int(elevation)
    
    return workout


# ========== CARDIOCOACH SYSTEM PROMPTS ==========

CARDIOCOACH_SYSTEM_EN = """You are CardioCoach, a mobile-first personal sports coach.
You answer user questions directly, like a human coach whispering in their ear.

THIS IS NOT A REPORT. THIS IS A CONVERSATION.

RESPONSE FORMAT (MANDATORY):

1) DIRECT ANSWER (required)
- 1 to 2 sentences maximum
- Directly answers the question
- Simple language
Example: "Your recent load is generally moderate, but quite irregular."

2) QUICK CONTEXT (optional)
- 1 to 3 bullet points maximum
- Each bullet = one key piece of information
- No unnecessary numbers
- No sub-sections
Example:
- Your last three runs were all at similar intensity
- Volume is slightly up from last week

3) COACH TIP (required)
- ONE single recommendation
- Clear, concrete, immediately actionable
Example: "Try to keep truly easy sessions between your harder outings."

STRICT STYLE RULES (FORBIDDEN):
- NO stars (*, **, ****)
- NO markdown
- NO titles or headers
- NO numbering (1., 2., etc.)
- NO sections like "physiological", "trend", "reading"
- NO walls of text
- NO artificial emphasis
- NO academic or medical tone

TONE:
- Calm
- Confident
- Caring
- Precise but simple
- Like a coach speaking in the user's ear

GOLDEN RULE:
If your response looks like a report or written analysis, it is WRONG and must be simplified.

100% ENGLISH. No French words allowed."""

CARDIOCOACH_SYSTEM_FR = """Tu es CardioCoach, un coach sportif personnel mobile-first.
Tu reponds directement aux questions de l'utilisateur, comme un coach humain qui parle a son oreille.

CECI N'EST PAS UN RAPPORT. C'EST UNE CONVERSATION.

FORMAT DE REPONSE (OBLIGATOIRE):

1) REPONSE DIRECTE (obligatoire)
- 1 a 2 phrases maximum
- Repond directement a la question
- Langage simple
Exemple: "Ta charge recente est globalement moderee, mais assez irreguliere."

2) CONTEXTE RAPIDE (optionnel)
- 1 a 3 puces maximum
- Chaque puce = une information cle
- Pas de chiffres inutiles
- Pas de sous-sections
Exemple:
- Tes trois dernieres sorties etaient toutes a intensite similaire
- Le volume est legerement en hausse par rapport a la semaine derniere

3) CONSEIL COACH (obligatoire)
- UNE seule recommandation
- Claire, concrete, immediatement applicable
Exemple: "Essaie de garder des seances vraiment faciles entre les sorties plus intenses."

REGLES DE STYLE STRICTES (INTERDITS):
- AUCUNE etoile (*, **, ****)
- AUCUN markdown
- AUCUN titre
- AUCUNE numerotation (1., 2., etc.)
- AUCUNE section "physiologique", "tendance", "lecture"
- AUCUN pave de texte
- AUCUNE emphase artificielle
- AUCUN ton academique ou medical

TON:
- Calme
- Confiant
- Bienveillant
- Precis mais simple
- Comme un coach qui parle dans l'oreille de l'utilisateur

REGLE D'OR:
Si ta reponse ressemble a un rapport ou a une analyse ecrite, elle est FAUSSE et doit etre simplifiee.

100% FRANCAIS. Aucun mot anglais autorise."""

DEEP_ANALYSIS_PROMPT_EN = """Provide a deep technical analysis of this workout WITH CONTEXTUAL COMPARISON to the athlete's recent baseline.

You have access to:
- Current workout data
- Baseline metrics from the last 7-14 days (averages and trends)

Structure your analysis:

1. EXECUTION ASSESSMENT
- How well was this session executed?
- Compare to recent baseline: pace/power consistency, heart rate response
- Express in relative terms: "slightly above your recent aerobic average", "in line with baseline", "notably higher than recent sessions"

2. TREND DETECTION
- Based on comparing this workout to baseline:
  - IMPROVING: metrics trending positively (lower HR at same pace, faster times, better efficiency)
  - MAINTAINING: stable performance, consistent with baseline
  - OVERLOAD RISK: signs of accumulated fatigue (elevated HR, declining pace, poor recovery between efforts)
- Be calm and precise. Not alarmist. State observations neutrally.

3. PHYSIOLOGICAL CONTEXT
- Zone distribution vs recent patterns
- Cardiac efficiency relative to baseline
- Any deviation from normal response patterns

4. ACTIONABLE INSIGHT
- One specific recommendation based on where this workout sits relative to recent load
- If load is high: suggest recovery focus
- If maintaining: suggest progression opportunity
- If improving: acknowledge and suggest next challenge

{hidden_insight_instruction}

Tone: Calm, precise, non-alarmist. Use phrases like:
- "slightly elevated compared to your recent baseline"
- "consistent with your 7-day average"
- "this represents a modest increase in training load"
- "your body is responding well to recent training"

Never dramatize. Just observe and advise."""

DEEP_ANALYSIS_PROMPT_FR = """Fournis une analyse technique approfondie de cette seance AVEC COMPARAISON CONTEXTUELLE a la baseline recente de l'athlete.

Tu as acces a:
- Les donnees de la seance actuelle
- Les metriques de reference des 7-14 derniers jours (moyennes et tendances)

Structure ton analyse:

1. EVALUATION DE L'EXECUTION
- Comment cette seance a-t-elle ete executee?
- Compare a la baseline recente: regularite allure/puissance, reponse cardiaque
- Exprime en termes relatifs: "legerement au-dessus de ta moyenne aerobie recente", "en ligne avec la baseline", "notablement plus eleve que les seances recentes"

2. DETECTION DE TENDANCE
- En comparant cette seance a la baseline:
  - PROGRESSION: metriques en amelioration (FC plus basse a meme allure, temps plus rapides, meilleure efficacite)
  - MAINTIEN: performance stable, coherente avec la baseline
  - RISQUE DE SURCHARGE: signes de fatigue accumulee (FC elevee, allure en baisse, mauvaise recuperation entre efforts)
- Sois calme et precis. Pas alarmiste. Enonce les observations de maniere neutre.

3. CONTEXTE PHYSIOLOGIQUE
- Distribution des zones vs patterns recents
- Efficacite cardiaque relative a la baseline
- Toute deviation des patterns de reponse normaux

4. RECOMMANDATION ACTIONNABLE
- Une recommandation specifique basee sur la position de cette seance par rapport a la charge recente
- Si charge elevee: suggere un focus recuperation
- Si maintien: suggere une opportunite de progression
- Si progression: reconnais et suggere le prochain defi

{hidden_insight_instruction}

Ton: Calme, precis, non-alarmiste. Utilise des phrases comme:
- "legerement eleve par rapport a ta baseline recente"
- "coherent avec ta moyenne sur 7 jours"
- "cela represente une augmentation modeste de la charge"
- "ton corps repond bien a l'entrainement recent"

Ne dramatise jamais. Observe et conseille simplement."""

HIDDEN_INSIGHT_EN = """
5. HIDDEN INSIGHT (include this section)
Add one non-obvious observation at the end. Something a less experienced coach might miss.

Focus areas (pick ONE that applies):
- Effort distribution anomaly: unusual zone transitions, split behavior patterns
- Pacing stability: drift patterns, negative/positive split tendencies
- Efficiency signals: pace-to-HR ratio changes, power economy shifts
- Fatigue fingerprints: late-session degradation, recovery interval quality
- Aerobic signature: threshold proximity patterns, sustainable effort markers

Rules:
- Variable length: sometimes just one sentence, sometimes 2-3 sentences
- No motivation ("great job", "keep it up")
- No alarms ("warning", "danger", "concerning")
- No medical terms
- State it as a quiet observation, like thinking out loud
- Use phrases like: "Worth noting...", "Something subtle here...", "An interesting pattern...", "One detail stands out..."

The goal is to sound like a thoughtful coach who notices things others don't."""

HIDDEN_INSIGHT_FR = """
5. OBSERVATION DISCRETE (inclure cette section)
Ajoute une observation non-evidente a la fin. Quelque chose qu'un coach moins experimente pourrait manquer.

Axes d'attention (choisis UN qui s'applique):
- Anomalie de distribution d'effort: transitions de zones inhabituelles, patterns de splits
- Stabilite d'allure: patterns de derive, tendances splits negatifs/positifs
- Signaux d'efficacite: changements du ratio allure/FC, evolution de l'economie de puissance
- Empreintes de fatigue: degradation en fin de seance, qualite des intervalles de recuperation
- Signature aerobie: patterns de proximite au seuil, marqueurs d'effort soutenable

Regles:
- Longueur variable: parfois une seule phrase, parfois 2-3 phrases
- Pas de motivation ("bravo", "continue comme ca")
- Pas d'alarmes ("attention", "danger", "preoccupant")
- Pas de termes medicaux
- Enonce-le comme une observation tranquille, comme une reflexion a voix haute
- Utilise des phrases comme: "A noter...", "Quelque chose de subtil ici...", "Un pattern interessant...", "Un detail ressort..."

L'objectif est de sonner comme un coach reflechi qui remarque des choses que d'autres ne voient pas."""

NO_HIDDEN_INSIGHT = ""

# ========== ADAPTIVE GUIDANCE PROMPTS ==========

ADAPTIVE_GUIDANCE_PROMPT_EN = """Based on the athlete's recent training data, provide adaptive training guidance.

You have access to:
- Recent workouts (last 7-14 days)
- Training load summary (volume, intensity distribution, workout types)

Generate SHORT-TERM guidance (not a rigid plan):

1. CURRENT STATUS
Assess the athlete's current state in ONE of these terms:
- "MAINTAIN" - training is balanced, continue current approach
- "ADJUST" - minor tweaks needed based on recent patterns
- "HOLD STEADY" - consolidate recent work before adding more

Explain in 1-2 sentences why.

2. SUGGESTED SESSIONS (max 3)
Provide up to 3 suggested next sessions. For each:
- Type: run/cycle/recovery
- Focus: what this session targets (aerobic base, speed, recovery, threshold, etc.)
- Duration/Distance: approximate
- Intensity: easy/moderate/hard or zone guidance
- Rationale: ONE sentence explaining "why this helps now" based on recent data

Format each suggestion as:
SESSION 1: [Type] - [Focus]
- Duration: [X min] or Distance: [X km]
- Intensity: [level]
- Why now: [brief rationale tied to recent training]

3. GUIDANCE NOTE (optional)
If relevant, add one brief observation about pacing, recovery, or load management.

Rules:
- No rigid schedules or fixed weekly plans
- Suggestions are guidance, not obligations
- Max 3 sessions ahead
- Calm, technical tone
- No motivation ("you've got this", "great work")
- No medical language
- No alarms or warnings
- Each suggestion must have a clear "why this helps now" rationale

The goal is to help the athlete train better without cognitive overload."""

ADAPTIVE_GUIDANCE_PROMPT_FR = """En fonction des donnees d'entrainement recentes de l'athlete, fournis des recommandations adaptatives.

Tu as acces a:
- Les seances recentes (7-14 derniers jours)
- Resume de la charge (volume, distribution d'intensite, types de seances)

Genere des recommandations A COURT TERME (pas un plan rigide):

1. STATUT ACTUEL
Evalue l'etat actuel de l'athlete avec UN de ces termes:
- "MAINTENIR" - l'entrainement est equilibre, continuer l'approche actuelle
- "AJUSTER" - petits ajustements necessaires selon les patterns recents
- "CONSOLIDER" - consolider le travail recent avant d'en ajouter

Explique en 1-2 phrases pourquoi.

2. SEANCES SUGGEREES (max 3)
Propose jusqu'a 3 prochaines seances. Pour chacune:
- Type: course/velo/recuperation
- Focus: ce que cette seance cible (base aerobie, vitesse, recuperation, seuil, etc.)
- Duree/Distance: approximative
- Intensite: facile/moderee/difficile ou zones
- Justification: UNE phrase expliquant "pourquoi maintenant" basee sur les donnees recentes

Formate chaque suggestion ainsi:
SEANCE 1: [Type] - [Focus]
- Duree: [X min] ou Distance: [X km]
- Intensite: [niveau]
- Pourquoi maintenant: [breve justification liee a l'entrainement recent]

3. NOTE DE GUIDANCE (optionnel)
Si pertinent, ajoute une breve observation sur l'allure, la recuperation ou la gestion de charge.

Regles:
- Pas de plannings rigides ou plans hebdomadaires fixes
- Les suggestions sont des recommandations, pas des obligations
- Max 3 seances a venir
- Ton calme et technique
- Pas de motivation ("tu vas y arriver", "super travail")
- Pas de langage medical
- Pas d'alarmes ou avertissements
- Chaque suggestion doit avoir une justification claire "pourquoi maintenant"

L'objectif est d'aider l'athlete a mieux s'entrainer sans surcharge cognitive."""


def get_system_prompt(language: str) -> str:
    """Get the appropriate system prompt based on language"""
    if language == "fr":
        return CARDIOCOACH_SYSTEM_FR
    return CARDIOCOACH_SYSTEM_EN


def calculate_baseline_metrics(workouts: List[dict], current_workout: dict, days: int = 14) -> dict:
    """Calculate baseline metrics from recent workouts for contextual comparison"""
    from datetime import datetime, timedelta
    
    current_date = datetime.fromisoformat(current_workout.get("date", "").replace("Z", "+00:00").split("T")[0])
    cutoff_date = current_date - timedelta(days=days)
    current_type = current_workout.get("type")
    
    # Filter workouts: same type, within date range, excluding current
    baseline_workouts = [
        w for w in workouts
        if w.get("type") == current_type
        and w.get("id") != current_workout.get("id")
        and w.get("date")
    ]
    
    # Filter by date
    filtered = []
    for w in baseline_workouts:
        try:
            w_date = datetime.fromisoformat(w["date"].replace("Z", "+00:00").split("T")[0])
            if cutoff_date <= w_date < current_date:
                filtered.append(w)
        except (ValueError, TypeError):
            continue
    
    if not filtered:
        return None
    
    # Calculate averages
    def safe_avg(values):
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 2) if valid else None
    
    baseline = {
        "period_days": days,
        "workout_count": len(filtered),
        "workout_type": current_type,
        "avg_distance_km": safe_avg([w.get("distance_km") for w in filtered]),
        "avg_duration_minutes": safe_avg([w.get("duration_minutes") for w in filtered]),
        "avg_heart_rate": safe_avg([w.get("avg_heart_rate") for w in filtered]),
        "avg_max_heart_rate": safe_avg([w.get("max_heart_rate") for w in filtered]),
    }
    
    # Type-specific metrics
    if current_type == "run":
        baseline["avg_pace_min_km"] = safe_avg([w.get("avg_pace_min_km") for w in filtered])
    elif current_type == "cycle":
        baseline["avg_speed_kmh"] = safe_avg([w.get("avg_speed_kmh") for w in filtered])
    
    # Calculate zone distribution averages
    zone_totals = {"z1": [], "z2": [], "z3": [], "z4": [], "z5": []}
    for w in filtered:
        zones = w.get("effort_zone_distribution", {})
        for z in zone_totals:
            if z in zones:
                zone_totals[z].append(zones[z])
    
    baseline["avg_zone_distribution"] = {
        z: safe_avg(vals) for z, vals in zone_totals.items() if vals
    }
    
    # Calculate load metrics
    total_volume = sum(w.get("distance_km", 0) for w in filtered)
    total_time = sum(w.get("duration_minutes", 0) for w in filtered)
    baseline["total_volume_km"] = round(total_volume, 1)
    baseline["total_time_minutes"] = total_time
    baseline["weekly_avg_distance"] = round(total_volume / (days / 7), 1) if days > 0 else 0
    
    # Compare current workout to baseline
    current_hr = current_workout.get("avg_heart_rate")
    current_dist = current_workout.get("distance_km")
    current_dur = current_workout.get("duration_minutes")
    
    comparison = {}
    if baseline["avg_heart_rate"] and current_hr:
        hr_diff = current_hr - baseline["avg_heart_rate"]
        hr_pct = (hr_diff / baseline["avg_heart_rate"]) * 100
        comparison["heart_rate_vs_baseline"] = {
            "difference_bpm": round(hr_diff, 1),
            "percentage": round(hr_pct, 1),
            "status": "elevated" if hr_pct > 5 else "reduced" if hr_pct < -5 else "normal"
        }
    
    if baseline["avg_distance_km"] and current_dist:
        dist_diff = current_dist - baseline["avg_distance_km"]
        dist_pct = (dist_diff / baseline["avg_distance_km"]) * 100
        comparison["distance_vs_baseline"] = {
            "difference_km": round(dist_diff, 1),
            "percentage": round(dist_pct, 1),
            "status": "longer" if dist_pct > 15 else "shorter" if dist_pct < -15 else "typical"
        }
    
    if current_type == "run" and baseline.get("avg_pace_min_km"):
        current_pace = current_workout.get("avg_pace_min_km")
        if current_pace:
            pace_diff = current_pace - baseline["avg_pace_min_km"]
            comparison["pace_vs_baseline"] = {
                "difference_min_km": round(pace_diff, 2),
                "status": "slower" if pace_diff > 0.15 else "faster" if pace_diff < -0.15 else "consistent"
            }
    
    baseline["comparison"] = comparison
    
    return baseline


# ========== MOCK DATA FOR DEMO ==========

def get_mock_workouts():
    """Generate mock workout data for demonstration with recent dates"""
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone.utc).date()
    
    return [
        {
            "id": "w001",
            "type": "run",
            "name": "Morning Easy Run",
            "date": (today - timedelta(days=0)).isoformat(),
            "duration_minutes": 45,
            "distance_km": 8.2,
            "avg_heart_rate": 142,
            "max_heart_rate": 158,
            "avg_pace_min_km": 5.49,
            "elevation_gain_m": 85,
            "calories": 520,
            "effort_zone_distribution": {"z1": 15, "z2": 55, "z3": 25, "z4": 5, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w002",
            "type": "cycle",
            "name": "Tempo Ride",
            "date": (today - timedelta(days=1)).isoformat(),
            "duration_minutes": 90,
            "distance_km": 42.5,
            "avg_heart_rate": 155,
            "max_heart_rate": 172,
            "avg_speed_kmh": 28.3,
            "elevation_gain_m": 320,
            "calories": 1180,
            "effort_zone_distribution": {"z1": 5, "z2": 25, "z3": 45, "z4": 20, "z5": 5},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w003",
            "type": "run",
            "name": "Interval Session",
            "date": (today - timedelta(days=2)).isoformat(),
            "duration_minutes": 52,
            "distance_km": 10.1,
            "avg_heart_rate": 162,
            "max_heart_rate": 185,
            "avg_pace_min_km": 5.15,
            "elevation_gain_m": 45,
            "calories": 680,
            "effort_zone_distribution": {"z1": 10, "z2": 20, "z3": 25, "z4": 30, "z5": 15},
            "notes": "5x1000m @ threshold",
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w004",
            "type": "run",
            "name": "Long Run",
            "date": (today - timedelta(days=3)).isoformat(),
            "duration_minutes": 105,
            "distance_km": 18.5,
            "avg_heart_rate": 138,
            "max_heart_rate": 155,
            "avg_pace_min_km": 5.68,
            "elevation_gain_m": 180,
            "calories": 1350,
            "effort_zone_distribution": {"z1": 20, "z2": 65, "z3": 15, "z4": 0, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w005",
            "type": "cycle",
            "name": "Recovery Spin",
            "date": (today - timedelta(days=4)).isoformat(),
            "duration_minutes": 45,
            "distance_km": 18.0,
            "avg_heart_rate": 118,
            "max_heart_rate": 132,
            "avg_speed_kmh": 24.0,
            "elevation_gain_m": 50,
            "calories": 380,
            "effort_zone_distribution": {"z1": 60, "z2": 35, "z3": 5, "z4": 0, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w006",
            "type": "run",
            "name": "Hill Repeats",
            "date": (today - timedelta(days=5)).isoformat(),
            "duration_minutes": 48,
            "distance_km": 8.8,
            "avg_heart_rate": 158,
            "max_heart_rate": 178,
            "avg_pace_min_km": 5.45,
            "elevation_gain_m": 280,
            "calories": 620,
            "effort_zone_distribution": {"z1": 10, "z2": 25, "z3": 30, "z4": 25, "z5": 10},
            "notes": "8x200m hill sprints",
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w007",
            "type": "cycle",
            "name": "Endurance Base",
            "date": (today - timedelta(days=6)).isoformat(),
            "duration_minutes": 120,
            "distance_km": 55.0,
            "avg_heart_rate": 135,
            "max_heart_rate": 152,
            "avg_speed_kmh": 27.5,
            "elevation_gain_m": 420,
            "calories": 1520,
            "effort_zone_distribution": {"z1": 15, "z2": 60, "z3": 20, "z4": 5, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # Baseline week (days 7-13)
        {
            "id": "w008",
            "type": "run",
            "name": "Recovery Run",
            "date": (today - timedelta(days=8)).isoformat(),
            "duration_minutes": 35,
            "distance_km": 6.0,
            "avg_heart_rate": 135,
            "max_heart_rate": 148,
            "avg_pace_min_km": 5.83,
            "elevation_gain_m": 40,
            "calories": 380,
            "effort_zone_distribution": {"z1": 25, "z2": 60, "z3": 15, "z4": 0, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w009",
            "type": "cycle",
            "name": "Steady Ride",
            "date": (today - timedelta(days=9)).isoformat(),
            "duration_minutes": 75,
            "distance_km": 35.0,
            "avg_heart_rate": 140,
            "max_heart_rate": 158,
            "avg_speed_kmh": 28.0,
            "elevation_gain_m": 250,
            "calories": 950,
            "effort_zone_distribution": {"z1": 10, "z2": 50, "z3": 30, "z4": 10, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w010",
            "type": "run",
            "name": "Tempo Run",
            "date": (today - timedelta(days=10)).isoformat(),
            "duration_minutes": 50,
            "distance_km": 10.0,
            "avg_heart_rate": 155,
            "max_heart_rate": 170,
            "avg_pace_min_km": 5.0,
            "elevation_gain_m": 60,
            "calories": 620,
            "effort_zone_distribution": {"z1": 5, "z2": 30, "z3": 45, "z4": 15, "z5": 5},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w011",
            "type": "run",
            "name": "Easy Run",
            "date": (today - timedelta(days=12)).isoformat(),
            "duration_minutes": 40,
            "distance_km": 7.5,
            "avg_heart_rate": 140,
            "max_heart_rate": 155,
            "avg_pace_min_km": 5.33,
            "elevation_gain_m": 50,
            "calories": 450,
            "effort_zone_distribution": {"z1": 20, "z2": 55, "z3": 20, "z4": 5, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "w012",
            "type": "cycle",
            "name": "Long Ride",
            "date": (today - timedelta(days=13)).isoformat(),
            "duration_minutes": 150,
            "distance_km": 70.0,
            "avg_heart_rate": 132,
            "max_heart_rate": 155,
            "avg_speed_kmh": 28.0,
            "elevation_gain_m": 550,
            "calories": 1850,
            "effort_zone_distribution": {"z1": 20, "z2": 60, "z3": 15, "z4": 5, "z5": 0},
            "notes": None,
            "data_source": "manual",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]


# ========== ROUTES ==========

@api_router.get("/")
async def root():
    return {"message": "CardioCoach API"}


@api_router.get("/workouts", response_model=List[dict])
async def get_workouts():
    """Get all workouts, sorted by date descending"""
    # Try to get from DB first, fall back to mock data
    workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(200)
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


# ========== VMA / VO2MAX ESTIMATION ==========

class VMAEstimationResponse(BaseModel):
    has_sufficient_data: bool
    confidence: str  # "high", "medium", "low", "insufficient"
    confidence_score: int  # 1-5 (5 = very confident)
    vma_kmh: Optional[float] = None
    vo2max: Optional[float] = None
    data_source: Optional[str] = None
    training_zones: Optional[dict] = None
    message: str
    recommendations: Optional[List[str]] = None


def estimate_vma_from_race(distance_km: float, time_minutes: int) -> dict:
    """Estimate VMA from race performance using VDOT tables (Jack Daniels)"""
    if distance_km <= 0 or time_minutes <= 0:
        return None
    
    # Calculate pace in min/km
    pace_min_km = time_minutes / distance_km
    
    # Simplified VDOT estimation based on pace
    # These are approximations from Jack Daniels' tables
    speed_kmh = 60 / pace_min_km  # Convert pace to km/h
    
    # VMA is approximately the speed you can sustain for 4-7 minutes
    # From race performance, we estimate VMA based on distance
    # Longer distances = lower % of VMA
    vma_percentage = {
        5: 0.95,      # 5km ≈ 95% VMA
        10: 0.90,     # 10km ≈ 90% VMA
        21.1: 0.85,   # Semi ≈ 85% VMA
        42.195: 0.80  # Marathon ≈ 80% VMA
    }
    
    # Find closest distance
    closest_dist = min(vma_percentage.keys(), key=lambda x: abs(x - distance_km))
    pct = vma_percentage[closest_dist]
    
    vma_kmh = speed_kmh / pct
    vo2max = vma_kmh * 3.5  # Standard formula: VO2max ≈ VMA × 3.5
    
    return {
        "vma_kmh": round(vma_kmh, 1),
        "vo2max": round(vo2max, 1),
        "method": "race_performance",
        "confidence": "high" if distance_km >= 5 else "medium"
    }


def estimate_vma_from_workouts(workouts: list) -> dict:
    """Estimate VMA from training data (Z5 efforts)"""
    
    # Filter running workouts with HR zones
    running_workouts = [
        w for w in workouts 
        if w.get("type") == "run" and w.get("effort_zone_distribution")
    ]
    
    if len(running_workouts) < 3:
        return {
            "has_sufficient_data": False,
            "reason": "need_more_workouts",
            "count": len(running_workouts)
        }
    
    # Analyze Z5 efforts
    z5_efforts = []
    z4_efforts = []
    
    for w in running_workouts:
        zones = w.get("effort_zone_distribution", {})
        z5_pct = zones.get("z5", 0) or 0
        z4_pct = zones.get("z4", 0) or 0
        duration = w.get("duration_minutes", 0)
        
        # Z5 time in minutes
        z5_time = (z5_pct / 100) * duration
        z4_time = (z4_pct / 100) * duration
        
        # Best pace as proxy for VMA effort
        best_pace = w.get("best_pace_min_km")
        avg_pace = w.get("avg_pace_min_km")
        
        if z5_time >= 2 and best_pace:  # At least 2 min in Z5
            z5_efforts.append({
                "workout": w.get("name"),
                "date": w.get("date"),
                "z5_time_min": z5_time,
                "best_pace": best_pace,
                "avg_pace": avg_pace
            })
        
        if z4_time >= 5 and avg_pace:  # At least 5 min in Z4
            z4_efforts.append({
                "workout": w.get("name"),
                "date": w.get("date"),
                "z4_time_min": z4_time,
                "avg_pace": avg_pace
            })
    
    # Priority 1: Use Z5 efforts (most reliable)
    if len(z5_efforts) >= 2:
        # Take best paces from Z5 efforts
        best_paces = [e["best_pace"] for e in z5_efforts if e["best_pace"]]
        if best_paces:
            # VMA ≈ best pace in Z5 (slightly faster)
            avg_best_pace = sum(best_paces) / len(best_paces)
            vma_kmh = 60 / avg_best_pace  # Convert min/km to km/h
            vo2max = vma_kmh * 3.5
            
            return {
                "has_sufficient_data": True,
                "vma_kmh": round(vma_kmh, 1),
                "vo2max": round(vo2max, 1),
                "method": "z5_efforts",
                "confidence": "medium",
                "sample_count": len(z5_efforts),
                "efforts": z5_efforts[:3]  # Return top 3 for reference
            }
    
    # Priority 2: Use Z4 efforts (less reliable)
    if len(z4_efforts) >= 3:
        avg_paces = [e["avg_pace"] for e in z4_efforts if e["avg_pace"]]
        if avg_paces:
            # Z4 pace ≈ 85-90% VMA, so VMA ≈ Z4 pace / 0.87
            avg_z4_pace = sum(avg_paces) / len(avg_paces)
            z4_speed = 60 / avg_z4_pace
            vma_kmh = z4_speed / 0.87
            vo2max = vma_kmh * 3.5
            
            return {
                "has_sufficient_data": True,
                "vma_kmh": round(vma_kmh, 1),
                "vo2max": round(vo2max, 1),
                "method": "z4_extrapolation",
                "confidence": "low",
                "sample_count": len(z4_efforts),
                "warning": "Estimation basée sur Z4 uniquement - moins fiable"
            }
    
    # Not enough high-intensity data
    return {
        "has_sufficient_data": False,
        "reason": "need_high_intensity",
        "z5_count": len(z5_efforts),
        "z4_count": len(z4_efforts)
    }


def calculate_training_zones(vma_kmh: float, language: str = "en") -> dict:
    """Calculate training zones based on VMA"""
    
    def kmh_to_pace(speed_kmh):
        if speed_kmh <= 0:
            return None
        pace = 60 / speed_kmh
        mins = int(pace)
        secs = int((pace - mins) * 60)
        return f"{mins}:{secs:02d}"
    
    zones = {
        "z1": {
            "name": "Recovery" if language == "en" else "Récupération",
            "pct_vma": "60-65%",
            "pace_range": f"{kmh_to_pace(vma_kmh * 0.60)} - {kmh_to_pace(vma_kmh * 0.65)}"
        },
        "z2": {
            "name": "Endurance" if language == "en" else "Endurance",
            "pct_vma": "65-75%",
            "pace_range": f"{kmh_to_pace(vma_kmh * 0.65)} - {kmh_to_pace(vma_kmh * 0.75)}"
        },
        "z3": {
            "name": "Tempo" if language == "en" else "Tempo",
            "pct_vma": "75-85%",
            "pace_range": f"{kmh_to_pace(vma_kmh * 0.75)} - {kmh_to_pace(vma_kmh * 0.85)}"
        },
        "z4": {
            "name": "Threshold" if language == "en" else "Seuil",
            "pct_vma": "85-95%",
            "pace_range": f"{kmh_to_pace(vma_kmh * 0.85)} - {kmh_to_pace(vma_kmh * 0.95)}"
        },
        "z5": {
            "name": "VMA/VO2max",
            "pct_vma": "95-105%",
            "pace_range": f"{kmh_to_pace(vma_kmh * 0.95)} - {kmh_to_pace(vma_kmh * 1.05)}"
        }
    }
    
    return zones


@api_router.get("/user/vma-estimate")
async def get_vma_estimate(user_id: str = "default", language: str = "en"):
    """Estimate VMA and VO2max from user data"""
    
    # Check if user has a goal (race performance to use)
    user_goal = await db.user_goals.find_one({"user_id": user_id}, {"_id": 0})
    
    # Get all running workouts
    all_workouts = await db.workouts.find(
        {"type": "run"}, 
        {"_id": 0}
    ).sort("date", -1).to_list(100)
    
    if not all_workouts:
        return VMAEstimationResponse(
            has_sufficient_data=False,
            confidence="insufficient",
            confidence_score=0,
            message="Données insuffisantes. Aucune séance de course enregistrée." if language == "fr" else "Insufficient data. No running workouts recorded.",
            recommendations=[
                "Synchronise tes séances Strava" if language == "fr" else "Sync your Strava workouts",
                "Fais quelques sorties avec cardiofréquencemètre" if language == "fr" else "Do some runs with heart rate monitor"
            ]
        )
    
    result = None
    data_source = None
    
    # Priority 1: Use goal race performance if it's a past event or use target
    if user_goal and user_goal.get("target_time_minutes") and user_goal.get("distance_km"):
        race_estimate = estimate_vma_from_race(
            user_goal["distance_km"],
            user_goal["target_time_minutes"]
        )
        if race_estimate:
            result = race_estimate
            data_source = f"Objectif: {user_goal['event_name']}" if language == "fr" else f"Goal: {user_goal['event_name']}"
    
    # Priority 2: Analyze workout data
    if not result:
        workout_estimate = estimate_vma_from_workouts(all_workouts)
        
        if not workout_estimate.get("has_sufficient_data"):
            reason = workout_estimate.get("reason")
            
            if reason == "need_more_workouts":
                msg = f"Données insuffisantes. Seulement {workout_estimate.get('count')} séances avec données cardio." if language == "fr" else f"Insufficient data. Only {workout_estimate.get('count')} workouts with HR data."
                recs = [
                    "Continue à synchroniser tes séances" if language == "fr" else "Keep syncing your workouts",
                    "Au moins 3 séances avec cardiofréquencemètre nécessaires" if language == "fr" else "At least 3 workouts with HR monitor needed"
                ]
            else:  # need_high_intensity
                msg = f"Données insuffisantes. Pas assez d'efforts intenses (Z4/Z5) pour estimer la VMA." if language == "fr" else f"Insufficient data. Not enough high-intensity efforts (Z4/Z5) to estimate VMA."
                recs = [
                    "Fais une séance de fractionné ou un test VMA" if language == "fr" else "Do an interval session or VMA test",
                    f"Séances Z5 trouvées: {workout_estimate.get('z5_count', 0)}, Z4: {workout_estimate.get('z4_count', 0)}"
                ]
            
            return VMAEstimationResponse(
                has_sufficient_data=False,
                confidence="insufficient",
                confidence_score=0,
                message=msg,
                recommendations=recs
            )
        
        result = workout_estimate
        method = result.get("method")
        if method == "z5_efforts":
            data_source = f"Analyse de {result.get('sample_count')} efforts Z5" if language == "fr" else f"Analysis of {result.get('sample_count')} Z5 efforts"
        else:
            data_source = f"Extrapolation depuis {result.get('sample_count')} séances Z4" if language == "fr" else f"Extrapolation from {result.get('sample_count')} Z4 sessions"
    
    # Calculate training zones
    vma_kmh = result["vma_kmh"]
    vo2max = result["vo2max"]
    training_zones = calculate_training_zones(vma_kmh, language)
    
    # Confidence mapping
    confidence = result.get("confidence", "medium")
    confidence_scores = {"high": 5, "medium": 3, "low": 2}
    confidence_score = confidence_scores.get(confidence, 1)
    
    # Build message
    if confidence == "high":
        msg = f"VMA estimée avec bonne fiabilité depuis ton objectif de course." if language == "fr" else "VMA estimated with good reliability from your race goal."
    elif confidence == "medium":
        msg = f"VMA estimée depuis tes efforts intenses. Fiabilité correcte." if language == "fr" else "VMA estimated from your intense efforts. Decent reliability."
    else:
        msg = f"VMA estimée par extrapolation. Fiabilité limitée - un test VMA serait plus précis." if language == "fr" else "VMA estimated by extrapolation. Limited reliability - a VMA test would be more accurate."
    
    # Recommendations based on VMA
    if language == "fr":
        recs = [
            f"Endurance fondamentale: {training_zones['z2']['pace_range']}/km",
            f"Allure seuil (tempo): {training_zones['z4']['pace_range']}/km",
            f"Fractionné VMA: {training_zones['z5']['pace_range']}/km"
        ]
    else:
        recs = [
            f"Easy/endurance pace: {training_zones['z2']['pace_range']}/km",
            f"Threshold (tempo) pace: {training_zones['z4']['pace_range']}/km",
            f"VMA intervals: {training_zones['z5']['pace_range']}/km"
        ]
    
    return VMAEstimationResponse(
        has_sufficient_data=True,
        confidence=confidence,
        confidence_score=confidence_score,
        vma_kmh=vma_kmh,
        vo2max=vo2max,
        data_source=data_source,
        training_zones=training_zones,
        message=msg,
        recommendations=recs
    )


# ========== DASHBOARD INSIGHT (DECISION ASSISTANT) ==========

DASHBOARD_INSIGHT_PROMPT_EN = """You are a calm, experienced running coach.
Generate ONE coaching sentence for the dashboard.

WEEK DATA: {week_data}
MONTH DATA: {month_data}

Rules:
- ONE sentence only, max 15 words
- Speak like a real coach, not a report
- Reassure and guide
- No numbers, no stats, no jargon
- The user should feel: "Ok, I understand. I know what to do."

Good examples:
- "Quiet week with just one run, makes sense for a restart."
- "Body is ready for a second easy outing."
- "Consistency matters more than intensity right now."

Bad (forbidden):
- "Volume analysis shows moderate load compared to baseline."
- Any mention of zones, bpm, or technical terms

100% ENGLISH only."""

DASHBOARD_INSIGHT_PROMPT_FR = """Tu es un coach running calme et experimente.
Genere UNE phrase de coaching pour le dashboard.

DONNEES SEMAINE: {week_data}
DONNEES MOIS: {month_data}

Regles:
- UNE seule phrase, max 15 mots
- Parle comme un vrai coach, pas comme un rapport
- Rassure et guide
- Pas de chiffres, pas de stats, pas de jargon
- L'utilisateur doit se dire: "Ok, je comprends. Je sais quoi faire."

Bons exemples:
- "Semaine tranquille avec une seule sortie, coherent pour une reprise."
- "Le corps est pret pour une deuxieme sortie facile."
- "La regularite compte plus que l'intensite pour l'instant."

Mauvais (interdit):
- "Analyse du volume montrant une charge moderee par rapport a la baseline."
- Toute mention de zones, bpm, ou termes techniques

100% FRANCAIS uniquement."""


class DashboardInsightResponse(BaseModel):
    coach_insight: str
    week: dict
    month: dict
    recovery_score: Optional[dict] = None  # New: recovery score


# ========== RECOVERY SCORE CALCULATION ==========

def calculate_recovery_score(workouts: list, language: str = "en") -> dict:
    """Calculate recovery score based on recent training load, intensity, and rest days"""
    today = datetime.now(timezone.utc).date()
    
    # Get workouts from last 7 days
    recent_workouts = []
    for w in workouts:
        try:
            w_date = datetime.fromisoformat(w.get("date", "").replace("Z", "+00:00").split("T")[0]).date()
            if (today - w_date).days <= 7:
                recent_workouts.append((w, w_date))
        except (ValueError, TypeError):
            continue
    
    # Get baseline (previous 7-14 days) for comparison
    baseline_workouts = []
    for w in workouts:
        try:
            w_date = datetime.fromisoformat(w.get("date", "").replace("Z", "+00:00").split("T")[0]).date()
            days_ago = (today - w_date).days
            if 7 < days_ago <= 14:
                baseline_workouts.append(w)
        except (ValueError, TypeError):
            continue
    
    # Calculate factors
    # 1. Days since last workout (more rest = higher recovery)
    if recent_workouts:
        last_workout_date = max(w_date for _, w_date in recent_workouts)
        days_since_last = (today - last_workout_date).days
    else:
        days_since_last = 7  # No recent workouts = well rested
    
    # 2. Load comparison (current vs baseline)
    current_load = sum(w.get("distance_km", 0) for w, _ in recent_workouts)
    baseline_load = sum(w.get("distance_km", 0) for w in baseline_workouts)
    
    if baseline_load > 0:
        load_ratio = current_load / baseline_load
    else:
        load_ratio = 1.0 if current_load == 0 else 1.5
    
    # 3. Intensity (hard sessions in last 3 days)
    hard_sessions_recent = 0
    for w, w_date in recent_workouts:
        if (today - w_date).days <= 3:
            zones = w.get("effort_zone_distribution", {})
            if zones:
                hard_pct = zones.get("z4", 0) + zones.get("z5", 0)
                if hard_pct >= 25:
                    hard_sessions_recent += 1
    
    # 4. Session spread (better if spread across days)
    unique_days = len(set(w_date for _, w_date in recent_workouts))
    
    # Calculate score (0-100)
    score = 100
    
    # Penalize if workout was today or yesterday
    if days_since_last == 0:
        score -= 25
    elif days_since_last == 1:
        score -= 15
    elif days_since_last >= 3:
        score += 5  # Bonus for extra rest
    
    # Penalize high load ratio
    if load_ratio > 1.3:
        score -= 20
    elif load_ratio > 1.15:
        score -= 10
    elif load_ratio < 0.7:
        score += 10  # Low load = more recovery
    
    # Penalize hard sessions
    score -= hard_sessions_recent * 15
    
    # Penalize clustered sessions
    if len(recent_workouts) > 0 and unique_days < len(recent_workouts):
        score -= 10  # Multiple sessions on same day
    
    # Clamp score
    score = max(20, min(100, score))
    
    # Determine status and coach phrase
    if score >= 75:
        status = "ready"
        if language == "fr":
            phrase = "Corps repose, pret pour une seance intense si tu veux."
        else:
            phrase = "Body is rested, ready for an intense session if you want."
    elif score >= 50:
        status = "moderate"
        if language == "fr":
            phrase = "Recuperation correcte, privilegie une seance facile."
        else:
            phrase = "Decent recovery, favor an easy session."
    else:
        status = "low"
        if language == "fr":
            phrase = "Fatigue accumulee, une journee de repos serait ideale."
        else:
            phrase = "Accumulated fatigue, a rest day would be ideal."
    
    return {
        "score": score,
        "status": status,
        "phrase": phrase,
        "days_since_last_workout": days_since_last
    }


# ========== USER GOALS ==========

# Distance types with km values
DISTANCE_TYPES = {
    "5k": 5.0,
    "10k": 10.0,
    "semi": 21.1,
    "marathon": 42.195,
    "ultra": 50.0  # Default for ultra, actual distance in event_name
}


def calculate_target_pace(distance_km: float, target_time_minutes: int) -> str:
    """Calculate target pace in min/km format"""
    if distance_km <= 0 or target_time_minutes <= 0:
        return None
    pace_minutes = target_time_minutes / distance_km
    pace_min = int(pace_minutes)
    pace_sec = int((pace_minutes - pace_min) * 60)
    return f"{pace_min}:{pace_sec:02d}"


def format_target_time(minutes: int) -> str:
    """Format target time as Xh:MM"""
    if not minutes:
        return None
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h{mins:02d}"
    return f"{mins}min"


class UserGoal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    event_name: str
    event_date: str  # ISO date string
    distance_type: str  # 5k, 10k, semi, marathon, ultra
    distance_km: float  # Actual distance in km
    target_time_minutes: Optional[int] = None  # Target time in minutes
    target_pace: Optional[str] = None  # Calculated pace min/km
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserGoalCreate(BaseModel):
    event_name: str
    event_date: str
    distance_type: str  # 5k, 10k, semi, marathon, ultra
    target_time_minutes: Optional[int] = None  # Target time in minutes


@api_router.get("/user/goal")
async def get_user_goal(user_id: str = "default"):
    """Get user's current goal"""
    goal = await db.user_goals.find_one({"user_id": user_id}, {"_id": 0})
    return goal


@api_router.post("/user/goal")
async def set_user_goal(goal: UserGoalCreate, user_id: str = "default"):
    """Set user's goal (event with date, distance, target time)"""
    # Delete existing goal
    await db.user_goals.delete_many({"user_id": user_id})
    
    # Get distance in km
    distance_km = DISTANCE_TYPES.get(goal.distance_type, 42.195)
    
    # Calculate target pace if time provided
    target_pace = None
    if goal.target_time_minutes:
        target_pace = calculate_target_pace(distance_km, goal.target_time_minutes)
    
    # Create new goal
    goal_obj = UserGoal(
        user_id=user_id,
        event_name=goal.event_name,
        event_date=goal.event_date,
        distance_type=goal.distance_type,
        distance_km=distance_km,
        target_time_minutes=goal.target_time_minutes,
        target_pace=target_pace
    )
    doc = goal_obj.model_dump()
    await db.user_goals.insert_one(doc)
    
    # Return without _id
    doc.pop("_id", None)
    
    logger.info(f"Goal set for user {user_id}: {goal.event_name} ({goal.distance_type}) on {goal.event_date}, target: {goal.target_time_minutes}min")
    return {"success": True, "goal": doc}


@api_router.delete("/user/goal")
async def delete_user_goal(user_id: str = "default"):
    """Delete user's goal"""
    result = await db.user_goals.delete_many({"user_id": user_id})
    return {"deleted": result.deleted_count > 0}


def calculate_week_stats(workouts: list) -> dict:
    """Calculate current week statistics"""
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    
    week_workouts = []
    for w in workouts:
        try:
            w_date = datetime.fromisoformat(w.get("date", "").replace("Z", "+00:00").split("T")[0]).date()
            if week_start <= w_date <= today:
                week_workouts.append(w)
        except (ValueError, TypeError):
            continue
    
    total_km = sum(w.get("distance_km", 0) for w in week_workouts)
    sessions = len(week_workouts)
    
    # Load signal based on volume vs typical week
    if total_km > 80:
        load_signal = "high"
    elif total_km > 40:
        load_signal = "balanced"
    else:
        load_signal = "low"
    
    return {
        "sessions": sessions,
        "volume_km": round(total_km, 1),
        "load_signal": load_signal
    }


def calculate_month_stats(workouts: list) -> dict:
    """Calculate last 30 days statistics"""
    today = datetime.now(timezone.utc).date()
    month_start = today - timedelta(days=30)
    prev_month_start = today - timedelta(days=60)
    
    current_month = []
    prev_month = []
    
    for w in workouts:
        try:
            w_date = datetime.fromisoformat(w.get("date", "").replace("Z", "+00:00").split("T")[0]).date()
            if month_start <= w_date <= today:
                current_month.append(w)
            elif prev_month_start <= w_date < month_start:
                prev_month.append(w)
        except (ValueError, TypeError):
            continue
    
    current_km = sum(w.get("distance_km", 0) for w in current_month)
    prev_km = sum(w.get("distance_km", 0) for w in prev_month)
    
    # Active weeks (weeks with at least one workout)
    active_weeks = len(set(
        datetime.fromisoformat(w.get("date", "").replace("Z", "+00:00").split("T")[0]).date().isocalendar()[1]
        for w in current_month if w.get("date")
    ))
    
    # Trend
    if prev_km > 0:
        change = (current_km - prev_km) / prev_km * 100
        if change > 15:
            trend = "up"
        elif change < -15:
            trend = "down"
        else:
            trend = "stable"
    else:
        trend = "up" if current_km > 0 else "stable"
    
    return {
        "volume_km": round(current_km, 1),
        "active_weeks": active_weeks,
        "trend": trend
    }


# Dashboard insight cache (5 minutes TTL)
_dashboard_cache = {}
DASHBOARD_CACHE_TTL = 300  # 5 minutes in seconds


@api_router.get("/dashboard/insight")
async def get_dashboard_insight(language: str = "fr", user_id: str = "default"):
    """Get dashboard coach insight with week and month summaries and recovery score - NO LLM"""
    
    # Check cache first
    cache_key = f"{user_id}_{language}"
    now = datetime.now(timezone.utc).timestamp()
    
    if cache_key in _dashboard_cache:
        cached_data, cached_time = _dashboard_cache[cache_key]
        if now - cached_time < DASHBOARD_CACHE_TTL:
            logger.info(f"Dashboard insight cache hit for {cache_key}")
            return cached_data
    
    # Get workouts
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(200)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # Calculate stats
    week_stats = calculate_week_stats(all_workouts)
    month_stats = calculate_month_stats(all_workouts)
    
    # Calculate recovery score
    recovery_score = calculate_recovery_score(all_workouts, language)
    
    # Generate insight using local engine (NO LLM)
    coach_insight = generate_dashboard_insight(
        week_stats=week_stats,
        month_stats=month_stats,
        recovery_score=recovery_score.get("score") if recovery_score else None,
        language=language
    )
    
    result = DashboardInsightResponse(
        coach_insight=coach_insight,
        week=week_stats,
        month=month_stats,
        recovery_score=recovery_score
    )
    
    # Store in cache
    _dashboard_cache[cache_key] = (result, now)
    logger.info(f"Dashboard insight cached for {cache_key}")
    
    return result


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
    """Get AI analysis from CardioCoach with persistent memory and contextual comparison"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    user_id = request.user_id or "default"
    language = request.language or "en"
    
    # Build context parts
    context_parts = []
    workout = None
    baseline = None
    
    # Get all workouts for baseline calculation
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(100)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # If specific workout requested, include its data
    if request.workout_id:
        workout = await db.workouts.find_one({"id": request.workout_id}, {"_id": 0})
        if not workout:
            workout = next((w for w in all_workouts if w["id"] == request.workout_id), None)
        
        if workout:
            context_parts.append(f"Current workout being analyzed:\n{workout}")
            
            # Calculate baseline metrics for contextual comparison
            baseline = calculate_baseline_metrics(all_workouts, workout, days=14)
            if baseline:
                context_parts.append(f"BASELINE METRICS (last {baseline['period_days']} days, {baseline['workout_count']} {baseline['workout_type']} sessions):\n{baseline}")
    
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
        # Determine if hidden insight should be included (60% probability)
        include_hidden_insight = random.random() < 0.6
        
        if include_hidden_insight:
            hidden_instruction = HIDDEN_INSIGHT_FR if language == "fr" else HIDDEN_INSIGHT_EN
        else:
            hidden_instruction = NO_HIDDEN_INSIGHT
        
        # Deep analysis mode with baseline comparison and optional hidden insight
        base_prompt = DEEP_ANALYSIS_PROMPT_FR if language == "fr" else DEEP_ANALYSIS_PROMPT_EN
        deep_prompt = base_prompt.format(hidden_insight_instruction=hidden_instruction)
        
        full_message = f"{deep_prompt}\n\nWorkout data:\n{workout}"
        if baseline:
            full_message += f"\n\nBaseline comparison data:\n{baseline}"
        
        logger.info(f"Deep analysis: hidden_insight={'included' if include_hidden_insight else 'skipped'}")
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


@api_router.post("/coach/guidance", response_model=GuidanceResponse)
async def get_adaptive_guidance(request: GuidanceRequest):
    """Generate adaptive training guidance based on recent workouts"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    language = request.language or "en"
    user_id = request.user_id or "default"
    
    # Get recent workouts (last 14 days)
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(100)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # Calculate training summary
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    cutoff_14d = today - timedelta(days=14)
    cutoff_7d = today - timedelta(days=7)
    
    recent_14d = []
    recent_7d = []
    
    for w in all_workouts:
        try:
            w_date = datetime.fromisoformat(w["date"].replace("Z", "+00:00").split("T")[0]).date()
            if w_date >= cutoff_14d:
                recent_14d.append(w)
            if w_date >= cutoff_7d:
                recent_7d.append(w)
        except (ValueError, TypeError, KeyError):
            continue
    
    # Build training summary
    def summarize_workouts(workouts):
        if not workouts:
            return {"count": 0, "total_km": 0, "total_min": 0, "by_type": {}}
        
        total_km = sum(w.get("distance_km", 0) for w in workouts)
        total_min = sum(w.get("duration_minutes", 0) for w in workouts)
        by_type = {}
        for w in workouts:
            t = w.get("type", "other")
            if t not in by_type:
                by_type[t] = {"count": 0, "km": 0, "min": 0}
            by_type[t]["count"] += 1
            by_type[t]["km"] += w.get("distance_km", 0)
            by_type[t]["min"] += w.get("duration_minutes", 0)
        
        return {
            "count": len(workouts),
            "total_km": round(total_km, 1),
            "total_min": total_min,
            "by_type": by_type
        }
    
    summary_14d = summarize_workouts(recent_14d)
    summary_7d = summarize_workouts(recent_7d)
    
    # Calculate intensity distribution from zone data
    zone_totals = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
    zone_count = 0
    for w in recent_14d:
        zones = w.get("effort_zone_distribution", {})
        if zones:
            for z, pct in zones.items():
                if z in zone_totals:
                    zone_totals[z] += pct
            zone_count += 1
    
    if zone_count > 0:
        avg_zones = {z: round(v / zone_count, 1) for z, v in zone_totals.items()}
    else:
        avg_zones = None
    
    # Build context for guidance
    context = f"""TRAINING DATA (Last 14 days):
- Sessions: {summary_14d['count']}
- Total distance: {summary_14d['total_km']} km
- Total time: {summary_14d['total_min']} minutes
- By type: {summary_14d['by_type']}

LAST 7 DAYS:
- Sessions: {summary_7d['count']}
- Total distance: {summary_7d['total_km']} km
- Total time: {summary_7d['total_min']} minutes

RECENT WORKOUTS (most recent first):
"""
    
    for w in recent_14d[:7]:
        context += f"- {w.get('date', 'N/A')}: {w.get('type', 'N/A')} - {w.get('name', 'N/A')}, {w.get('distance_km', 0)}km, {w.get('duration_minutes', 0)}min, HR {w.get('avg_heart_rate', 'N/A')}\n"
    
    if avg_zones:
        context += f"\nAVERAGE ZONE DISTRIBUTION (14d): {avg_zones}"
    
    # Get guidance prompt
    guidance_prompt = ADAPTIVE_GUIDANCE_PROMPT_FR if language == "fr" else ADAPTIVE_GUIDANCE_PROMPT_EN
    full_message = f"{guidance_prompt}\n\n{context}"
    
    try:
        session_id = f"guidance_{user_id}"
        system_prompt = get_system_prompt(language)
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=full_message)
        response = await chat.send_message(user_message)
        
        # Determine status from response
        response_upper = response.upper()
        if "MAINTAIN" in response_upper or "MAINTENIR" in response_upper:
            status = "maintain"
        elif "ADJUST" in response_upper or "AJUSTER" in response_upper:
            status = "adjust"
        elif "HOLD" in response_upper or "CONSOLIDER" in response_upper:
            status = "hold_steady"
        else:
            status = "maintain"  # Default
        
        # Store guidance in DB
        await db.guidance.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "status": status,
            "guidance": response,
            "language": language,
            "training_summary": {
                "last_14d": summary_14d,
                "last_7d": summary_7d
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Guidance generated: status={status}, user={user_id}")
        
        return GuidanceResponse(
            status=status,
            guidance=response,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
    
    except Exception as e:
        logger.error(f"Guidance generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Guidance generation failed: {str(e)}")


@api_router.get("/coach/guidance/latest")
async def get_latest_guidance(user_id: str = "default"):
    """Get the most recent guidance for a user"""
    guidance = await db.guidance.find_one(
        {"user_id": user_id},
        {"_id": 0},
        sort=[("generated_at", -1)]
    )
    if not guidance:
        return None
    return guidance


# ========== WEEKLY REVIEW (BILAN DE LA SEMAINE) ==========

class WeeklyReviewResponse(BaseModel):
    period_start: str
    period_end: str
    coach_summary: str  # 1 phrase max - CARTE 1
    coach_reading: str  # 2-3 phrases - CARTE 4
    recommendations: List[str]  # 1-2 actions - CARTE 5
    recommendations_followup: Optional[str] = None  # Feedback on last week's recommendations
    metrics: dict  # CARTE 3
    comparison: dict  # vs semaine precedente
    signals: List[dict]  # CARTE 2
    user_goal: Optional[dict] = None  # User's event goal
    generated_at: str


WEEKLY_REVIEW_PROMPT_EN = """You are a calm, experienced professional coach giving a weekly review.
The user should understand their week in under 1 minute and know what to do next week.

CURRENT WEEK DATA: {training_data}
PREVIOUS WEEK DATA: {baseline_data}
{goal_context}
{followup_context}

KEY METRICS TO USE IN YOUR ANALYSIS:
- HR Zone distribution: Aggregate Z1-Z5 percentages show training intensity balance
  (Ideal polarized: 80% easy Z1-Z2, 20% hard Z4-Z5)
- Average cadence: Running efficiency indicator (optimal 170-180 spm)
- Pace consistency: Low variability = steady runs, high = intervals or terrain

Respond in JSON format only:
{{
  "coach_summary": "<ONE sentence maximum. Include zone insight if relevant. Example: 'Good volume with mostly easy effort - classic endurance building week.'>",
  "coach_reading": "<2 to 3 sentences ONLY. Interpret zones and intensity balance. Example: 'You spent 70% in Z4 this week which is high intensity. Consider adding more Z2 runs for recovery. Cadence averaged 165, try shorter steps for efficiency.'>",
  "recommendations": [
    "<1 to 2 clear recommendations based on zone analysis. ACTION-oriented. Example: 'Add a pure Z2 recovery run (conversational pace)'>",
    "<Example: 'Work on cadence: aim for 170+ spm on easy runs'>"
  ],
  "recommendations_followup": "<ONLY if previous recommendations exist: ONE sentence about how the user followed (or not) last week's advice. Be factual, not judgmental. Leave empty string if no previous recommendations.>"
}}

TRANSLATE zones naturally: Z1-Z2="easy/recovery", Z3="moderate", Z4="hard/tempo", Z5="max effort"
FORBIDDEN: Raw percentages without context, markdown, report language
REQUIRED: Interpret data into simple coaching insights. Calm, confident, professional.

100% ENGLISH only. No French words."""

WEEKLY_REVIEW_PROMPT_FR = """Tu es un coach professionnel calme et experimente qui fait un bilan hebdomadaire.
L'utilisateur doit comprendre sa semaine en moins d'1 minute et savoir quoi faire la semaine prochaine.

DONNEES SEMAINE EN COURS: {training_data}
DONNEES SEMAINE PRECEDENTE: {baseline_data}
{goal_context}
{followup_context}

METRIQUES CLES POUR TON ANALYSE:
- Repartition zones FC: Agregation Z1-Z5 montre l'equilibre d'intensite
  (Ideal polarise: 80% facile Z1-Z2, 20% dur Z4-Z5)
- Cadence moyenne: Indicateur d'efficacite (optimal 170-180 ppm)
- Regularite allure: Basse variabilite = sorties regulieres, haute = intervalles ou terrain

Reponds en format JSON uniquement:
{{
  "coach_summary": "<UNE phrase maximum. Inclus insight zones si pertinent. Exemple: 'Bon volume avec effort surtout facile - semaine classique de construction.'>",
  "coach_reading": "<2 a 3 phrases UNIQUEMENT. Interprete zones et equilibre intensite. Exemple: 'Tu as passe 70% en Z4 cette semaine, intensite elevee. Ajoute des sorties Z2 pour recuperer. Cadence moyenne 165, essaie des foulees plus courtes.'>",
  "recommendations": [
    "<1 a 2 recommandations claires basees sur analyse zones. Orientees ACTION. Exemple: 'Ajouter une sortie pure Z2 (allure conversation)'>",
    "<Exemple: 'Travailler la cadence: viser 170+ ppm sur sorties faciles'>"
  ],
  "recommendations_followup": "<UNIQUEMENT si recommandations precedentes existent: UNE phrase sur comment l'utilisateur a suivi (ou non) les conseils. Factuel, pas moralisateur. Vide si pas de recommandations precedentes.>"
}}

TRADUIRE les zones naturellement: Z1-Z2="facile/recup", Z3="modere", Z4="soutenu/tempo", Z5="effort max"
INTERDIT: Pourcentages bruts sans contexte, markdown, langage de rapport
OBLIGATOIRE: Interprete les donnees en coaching simple. Calme, confiant, professionnel.

100% FRANCAIS uniquement. Aucun mot anglais."""


def calculate_review_metrics(workouts: List[dict], baseline_workouts: List[dict]) -> tuple:
    """Calculate metrics and comparison for weekly review"""
    if not workouts:
        metrics = {
            "total_sessions": 0,
            "total_distance_km": 0,
            "total_duration_min": 0,
        }
        comparison = {
            "sessions_diff": 0,
            "distance_diff_km": 0,
            "distance_diff_pct": 0,
            "duration_diff_min": 0,
        }
        return metrics, comparison
    
    # Current week metrics
    total_distance = sum(w.get("distance_km", 0) for w in workouts)
    total_duration = sum(w.get("duration_minutes", 0) for w in workouts)
    
    metrics = {
        "total_sessions": len(workouts),
        "total_distance_km": round(total_distance, 1),
        "total_duration_min": total_duration,
    }
    
    # Baseline comparison
    baseline_sessions = len(baseline_workouts) if baseline_workouts else 0
    baseline_distance = sum(w.get("distance_km", 0) for w in baseline_workouts) if baseline_workouts else 0
    baseline_duration = sum(w.get("duration_minutes", 0) for w in baseline_workouts) if baseline_workouts else 0
    
    # Calculate differences
    distance_diff_pct = 0
    if baseline_distance > 0:
        distance_diff_pct = round(((total_distance - baseline_distance) / baseline_distance) * 100)
    elif total_distance > 0:
        distance_diff_pct = 100
    
    comparison = {
        "sessions_diff": len(workouts) - baseline_sessions,
        "distance_diff_km": round(total_distance - baseline_distance, 1),
        "distance_diff_pct": distance_diff_pct,
        "duration_diff_min": total_duration - baseline_duration,
    }
    
    return metrics, comparison


def generate_review_signals(workouts: List[dict], baseline_workouts: List[dict]) -> List[dict]:
    """Generate visual signal indicators for weekly review - CARTE 2"""
    signals = []
    
    # Calculate volume change
    current_km = sum(w.get("distance_km", 0) for w in workouts)
    baseline_km = sum(w.get("distance_km", 0) for w in baseline_workouts) if baseline_workouts else 0
    
    if baseline_km > 0:
        volume_change = round(((current_km - baseline_km) / baseline_km) * 100)
    else:
        volume_change = 100 if current_km > 0 else 0
    
    # Volume signal
    if volume_change > 15:
        signals.append({"key": "load", "status": "up", "value": f"+{volume_change}%"})
    elif volume_change < -15:
        signals.append({"key": "load", "status": "down", "value": f"{volume_change}%"})
    else:
        signals.append({"key": "load", "status": "stable", "value": f"{volume_change:+}%" if volume_change != 0 else "="})
    
    # Intensity signal based on zone distribution
    zone_totals = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
    zone_count = 0
    for w in workouts:
        zones = w.get("effort_zone_distribution", {})
        if zones:
            for z, pct in zones.items():
                if z in zone_totals:
                    zone_totals[z] += pct
            zone_count += 1
    
    if zone_count > 0:
        avg_zones = {z: v / zone_count for z, v in zone_totals.items()}
        easy_pct = avg_zones.get("z1", 0) + avg_zones.get("z2", 0)
        hard_pct = avg_zones.get("z4", 0) + avg_zones.get("z5", 0)
        
        if easy_pct >= 70:
            signals.append({"key": "intensity", "status": "easy", "value": None})
        elif hard_pct >= 30:
            signals.append({"key": "intensity", "status": "hard", "value": None})
        else:
            signals.append({"key": "intensity", "status": "balanced", "value": None})
    else:
        signals.append({"key": "intensity", "status": "balanced", "value": None})
    
    # Regularity signal (sessions spread across days)
    unique_days = len(set(w.get("date", "")[:10] for w in workouts))
    regularity_pct = min(100, round((unique_days / 7) * 100)) if workouts else 0
    
    if regularity_pct >= 60:
        signals.append({"key": "consistency", "status": "high", "value": f"{regularity_pct}%"})
    elif regularity_pct >= 30:
        signals.append({"key": "consistency", "status": "moderate", "value": f"{regularity_pct}%"})
    else:
        signals.append({"key": "consistency", "status": "low", "value": f"{regularity_pct}%"})
    
    return signals


@api_router.get("/coach/digest")
async def get_weekly_review(user_id: str = "default", language: str = "fr"):
    """Generate weekly training review (Bilan de la semaine) - 100% LOCAL ENGINE, NO LLM"""
    
    # Get all workouts
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(200)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # Calculate date ranges
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=7)
    baseline_start = today - timedelta(days=14)
    
    # Filter workouts for current week and baseline
    current_week = []
    baseline_week = []
    
    for w in all_workouts:
        try:
            w_date = datetime.fromisoformat(w["date"].replace("Z", "+00:00").split("T")[0]).date()
            if week_start <= w_date <= today:
                current_week.append(w)
            elif baseline_start <= w_date < week_start:
                baseline_week.append(w)
        except (ValueError, TypeError, KeyError):
            continue
    
    # Calculate metrics and comparison (CARTE 3)
    metrics, comparison = calculate_review_metrics(current_week, baseline_week)
    
    # Generate signals (CARTE 2)
    signals = generate_review_signals(current_week, baseline_week)
    
    # Get user goal for context
    user_goal = await db.user_goals.find_one({"user_id": user_id}, {"_id": 0})
    
    # Generate review content using LOCAL ENGINE (NO LLM - Strava compliant)
    review = generate_weekly_review(
        workouts=current_week,
        previous_week_workouts=baseline_week,
        user_goal=user_goal,
        language=language
    )
    
    coach_summary = review["summary"]
    coach_reading = review["meaning"]
    recommendations = [review["advice"]]
    recommendations_followup = review.get("recovery", "")
    
    # Store review
    review_id = str(uuid.uuid4())
    await db.digests.insert_one({
        "id": review_id,
        "user_id": user_id,
        "period_start": week_start.isoformat(),
        "period_end": today.isoformat(),
        "coach_summary": coach_summary,
        "coach_reading": coach_reading,
        "recommendations": recommendations,
        "recommendations_followup": recommendations_followup,
        "metrics": metrics,
        "comparison": comparison,
        "signals": signals,
        "user_goal": user_goal,
        "language": language,
        "generated_at": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Weekly review generated for user {user_id}: {len(current_week)} workouts (LOCAL ENGINE)")
    
    return WeeklyReviewResponse(
        period_start=week_start.isoformat(),
        period_end=today.isoformat(),
        coach_summary=coach_summary,
        coach_reading=coach_reading,
        recommendations=recommendations,
        recommendations_followup=recommendations_followup,
        metrics=metrics,
        comparison=comparison,
        signals=signals,
        user_goal=user_goal,
        generated_at=datetime.now(timezone.utc).isoformat()
    )


@api_router.get("/coach/digest/latest")
async def get_latest_digest(user_id: str = "default"):
    """Get the most recent digest for a user"""
    digest = await db.digests.find_one(
        {"user_id": user_id},
        {"_id": 0},
        sort=[("generated_at", -1)]
    )
    return digest


# ========== MOBILE-FIRST WORKOUT ANALYSIS ==========

MOBILE_ANALYSIS_PROMPT_EN = """You are a calm running coach giving quick feedback on a workout.

WORKOUT DATA:
{workout_data}

RECENT HABITS (baseline):
{baseline_data}

KEY METRICS TO ANALYZE:
- HR Zones: Time distribution across Z1-Z5 (Z1-Z2 = easy, Z3 = moderate, Z4-Z5 = hard)
- Pace: Average vs best pace, variability (low = steady, high = variable effort)
- Cadence: Steps per minute (optimal running: 170-180 spm)
- Compare this session to recent habits

Respond in JSON:
{{
  "coach_summary": "<ONE sentence, max 15 words. Like a coach talking. Use HR zones insight. Example: 'Mostly in Z4, a solid tempo run with good rhythm.'>",
  "insight": "<Max 2 short sentences. Interpret the data simply. Example: 'You spent 65% in Z4 which shows sustained effort. Cadence at 165 is slightly low.'>",
  "guidance": "<ONE calm suggestion based on zones/pace or null. Example: 'Next time, try more Z2 time to balance the week.'>"
}}

FORBIDDEN: raw numbers without context, markdown, "baseline", "distribution", report language
TRANSLATE zones to feelings: Z1-Z2="easy/comfortable", Z3="moderate", Z4="hard/tempo", Z5="max effort"
REQUIRED: Speak like a real coach. Reassure. Guide. Keep it simple but informed.

100% ENGLISH only."""

MOBILE_ANALYSIS_PROMPT_FR = """Tu es un coach running calme qui donne un retour rapide sur une seance.

DONNEES SEANCE:
{workout_data}

HABITUDES RECENTES (baseline):
{baseline_data}

METRIQUES CLES A ANALYSER:
- Zones FC: Repartition Z1-Z5 (Z1-Z2 = facile, Z3 = modere, Z4-Z5 = soutenu)
- Allure: Moyenne vs meilleure, variabilite (basse = regulier, haute = effort variable)
- Cadence: Pas par minute (optimal course: 170-180 ppm)
- Compare cette seance aux habitudes recentes

Reponds en JSON:
{{
  "coach_summary": "<UNE phrase, max 15 mots. Comme un coach qui parle. Utilise les zones. Exemple: 'Surtout en Z4, une belle sortie tempo avec bon rythme.'>",
  "insight": "<Max 2 phrases courtes. Interprete les donnees simplement. Exemple: 'Tu as passe 65% en Z4, effort soutenu. Cadence a 165, un peu basse.'>",
  "guidance": "<UNE suggestion calme basee sur zones/allure ou null. Exemple: 'Prochaine fois, plus de temps en Z2 pour equilibrer la semaine.'>"
}}

INTERDIT: chiffres bruts sans contexte, markdown, "baseline", "distribution", langage de rapport
TRADUIRE les zones en sensations: Z1-Z2="facile/confortable", Z3="modere", Z4="soutenu/tempo", Z5="effort max"
OBLIGATOIRE: Parle comme un vrai coach. Rassure. Guide. Simple mais informe.

100% FRANCAIS uniquement."""


class MobileAnalysisResponse(BaseModel):
    workout_id: str
    coach_summary: str
    intensity: dict
    load: dict
    session_type: dict
    insight: Optional[str] = None
    guidance: Optional[str] = None


def calculate_mobile_signals(workout: dict, baseline: dict) -> dict:
    """Calculate signal cards for mobile workout analysis"""
    w_type = workout.get("type", "run")
    
    # Intensity card
    intensity = {
        "pace": None,
        "avg_hr": workout.get("avg_heart_rate"),
        "label": "normal"
    }
    
    if w_type == "run":
        pace = workout.get("avg_pace_min_km")
        if pace:
            mins = int(pace)
            secs = int((pace - mins) * 60)
            intensity["pace"] = f"{mins}:{str(secs).zfill(2)}/km"
    else:
        speed = workout.get("avg_speed_kmh")
        if speed:
            intensity["pace"] = f"{speed:.1f} km/h"
    
    # Compare HR to baseline for intensity label
    hr_score = 0
    if baseline and baseline.get("avg_heart_rate") and workout.get("avg_heart_rate"):
        hr_diff_pct = (workout["avg_heart_rate"] - baseline["avg_heart_rate"]) / baseline["avg_heart_rate"] * 100
        if hr_diff_pct > 5:
            intensity["label"] = "above_usual"
            hr_score = 1
        elif hr_diff_pct < -5:
            intensity["label"] = "below_usual"
            hr_score = -1
    
    # Load card
    distance = workout.get("distance_km", 0)
    duration = workout.get("duration_minutes", 0)
    
    load = {
        "distance_km": round(distance, 1),
        "duration_min": duration,
        "direction": "stable"
    }
    
    load_score = 0
    if baseline and baseline.get("avg_distance_km"):
        dist_diff = (distance - baseline["avg_distance_km"]) / baseline["avg_distance_km"] * 100
        if dist_diff > 15:
            load["direction"] = "up"
            load_score = 1
        elif dist_diff < -15:
            load["direction"] = "down"
            load_score = -1
    
    # Session Type card (Easy / Sustained / Hard)
    # Based on HR intensity + load combined
    combined_score = hr_score + load_score
    
    if combined_score >= 2:
        session_type_label = "hard"
    elif combined_score <= -1:
        session_type_label = "easy"
    elif hr_score == 1 or load_score == 1:
        session_type_label = "sustained"
    else:
        session_type_label = "easy" if hr_score == -1 else "sustained"
    
    # Also check zone distribution if available
    zones = workout.get("effort_zone_distribution", {})
    if zones:
        hard_zones = (zones.get("z4", 0) or 0) + (zones.get("z5", 0) or 0)
        easy_zones = (zones.get("z1", 0) or 0) + (zones.get("z2", 0) or 0)
        
        if hard_zones > 30:
            session_type_label = "hard"
        elif easy_zones > 80:
            session_type_label = "easy"
    
    session_type = {
        "label": session_type_label
    }
    
    return {
        "intensity": intensity,
        "load": load,
        "session_type": session_type
    }


@api_router.get("/coach/workout-analysis/{workout_id}")
async def get_mobile_workout_analysis(workout_id: str, language: str = "fr", user_id: str = "default"):
    """Get mobile-first workout analysis with coach summary and signals - 100% LOCAL ENGINE"""
    
    # Get all workouts
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(100)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # Find the workout
    workout = await db.workouts.find_one({"id": workout_id}, {"_id": 0})
    if not workout:
        workout = next((w for w in all_workouts if w["id"] == workout_id), None)
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Calculate baseline
    baseline = calculate_baseline_metrics(all_workouts, workout, days=14)
    
    # Calculate signal cards
    signals = calculate_mobile_signals(workout, baseline)
    
    # Build workout summary for AI with enriched data
    workout_summary = {
        "type": workout.get("type"),
        "distance_km": workout.get("distance_km"),
        "duration_min": workout.get("duration_minutes"),
        "moving_time_min": workout.get("moving_time_minutes"),
        "avg_hr": workout.get("avg_heart_rate"),
        "max_hr": workout.get("max_heart_rate"),
        "hr_zones": workout.get("effort_zone_distribution"),
        "avg_pace_min_km": workout.get("avg_pace_min_km"),
        "best_pace_min_km": workout.get("best_pace_min_km"),
        "pace_variability": workout.get("pace_stats", {}).get("pace_variability") if workout.get("pace_stats") else None,
        "avg_cadence_spm": workout.get("avg_cadence_spm"),
        "avg_speed_kmh": workout.get("avg_speed_kmh"),
        "max_speed_kmh": workout.get("max_speed_kmh"),
        "elevation_m": workout.get("elevation_gain_m")
    }
    
    baseline_summary = {
        "sessions": baseline.get("workout_count", 0) if baseline else 0,
        "avg_distance": baseline.get("avg_distance_km") if baseline else None,
        "avg_duration": baseline.get("avg_duration_min") if baseline else None,
        "avg_hr": baseline.get("avg_heart_rate") if baseline else None,
        "avg_pace": baseline.get("avg_pace") if baseline else None,
        "avg_cadence": baseline.get("avg_cadence") if baseline else None
    } if baseline else {}
    
    # Generate analysis using LOCAL ENGINE (NO LLM - Strava compliant)
    analysis = generate_session_analysis(workout, baseline, language)
    
    coach_summary = analysis["summary"]
    insight = analysis["meaning"]
    guidance = analysis["advice"]
    
    return MobileAnalysisResponse(
        workout_id=workout_id,
        coach_summary=coach_summary,
        intensity=signals["intensity"],
        load=signals["load"],
        session_type=signals["session_type"],
        insight=insight,
        guidance=guidance
    )


# ========== DETAILED ANALYSIS (CARD-BASED MOBILE) ==========

DETAILED_ANALYSIS_PROMPT_EN = """You are a calm running coach giving a detailed debrief.
This is NOT a report. This is a calm conversation with data-informed insights.

WORKOUT DATA:
{workout_data}

RECENT HABITS (baseline):
{baseline_data}

KEY DATA TO INTERPRET:
- HR Zones (z1-z5): z1-z2 = recovery/easy, z3 = aerobic, z4 = tempo/threshold, z5 = VO2max
- Pace: avg vs best shows your range, variability shows steadiness
- Cadence: 170-180 spm is efficient, <165 may indicate overstriding

Structure your response in JSON:

{{
  "header": {{
    "context": "<1 sentence. What happened using zone insight. Example: '65% in Z4 - a solid tempo effort with good rhythm.'>",
    "session_name": "<Short descriptive name based on zones. Example: 'Tempo Run' if mostly Z4, 'Easy Aerobic' if Z1-Z2>"
  }},
  "execution": {{
    "intensity": "<Easy | Moderate | Sustained | High> - based on Z4+Z5 percentage",
    "volume": "<Usual | Longer | One-off peak>",
    "regularity": "<Stable | Variable> - based on pace variability"
  }},
  "meaning": {{
    "text": "<What it means. 2-3 short sentences. Interpret zones and pace. Example: 'Most time in Z4 shows sustained threshold work. Your cadence at 165 is slightly low - small steps help efficiency. Pace variability was high, suggesting uneven terrain or effort.'>"
  }},
  "recovery": {{
    "text": "<What the body needs based on intensity. 1 sentence. Example: 'After that Z4 effort, an easy Z2 day tomorrow helps absorption.'>"
  }},
  "advice": {{
    "text": "<What to do next. 1 calm sentence. Example: 'Next run, aim for more Z2 time to balance this tempo work.'>"
  }},
  "advanced": {{
    "comparisons": "<Technical details for curious users. 2-3 short points about zones/pace/cadence vs baseline.>"
  }}
}}

TRANSLATE zones: Z1-Z2="easy/recovery", Z3="aerobic", Z4="tempo/hard", Z5="max"
FORBIDDEN: raw zone percentages without interpretation, markdown, report language
REQUIRED: Interpret data into actionable coaching. Reassure. Guide.

100% ENGLISH only."""

DETAILED_ANALYSIS_PROMPT_FR = """Tu es un coach running calme qui fait un debrief detaille.
Ceci n'est PAS un rapport. C'est une conversation calme avec des insights bases sur les donnees.

DONNEES SEANCE:
{workout_data}

HABITUDES RECENTES (baseline):
{baseline_data}

DONNEES CLES A INTERPRETER:
- Zones FC (z1-z5): z1-z2 = recup/facile, z3 = aerobie, z4 = tempo/seuil, z5 = VO2max
- Allure: moy vs meilleure montre ta plage, variabilite montre la regularite
- Cadence: 170-180 ppm est efficace, <165 peut indiquer des foulees trop longues

Structure ta reponse en JSON:

{{
  "header": {{
    "context": "<1 phrase. Ce qui s'est passe avec insight zones. Exemple: '65% en Z4 - un bel effort tempo avec bon rythme.'>",
    "session_name": "<Nom court descriptif base sur zones. Exemple: 'Sortie Tempo' si surtout Z4, 'Aerobie Facile' si Z1-Z2>"
  }},
  "execution": {{
    "intensity": "<Facile | Moderee | Soutenue | Haute> - base sur pourcentage Z4+Z5",
    "volume": "<Habituel | Plus long | Pic ponctuel>",
    "regularity": "<Stable | Variable> - base sur variabilite allure"
  }},
  "meaning": {{
    "text": "<Ce que ca signifie. 2-3 phrases courtes. Interprete zones et allure. Exemple: 'Surtout en Z4, travail au seuil soutenu. Ta cadence a 165 est un peu basse - des petits pas aident l'efficacite. Variabilite d'allure elevee, terrain vallonne ou effort irregulier.'>"
  }},
  "recovery": {{
    "text": "<Ce dont le corps a besoin selon l'intensite. 1 phrase. Exemple: 'Apres cet effort Z4, une journee facile en Z2 demain aide l'absorption.'>"
  }},
  "advice": {{
    "text": "<Quoi faire ensuite. 1 phrase calme. Exemple: 'Prochaine sortie, vise plus de temps en Z2 pour equilibrer ce tempo.'>"
  }},
  "advanced": {{
    "comparisons": "<Details techniques pour les curieux. 2-3 points courts sur zones/allure/cadence vs baseline.>"
  }}
}}

TRADUIRE les zones: Z1-Z2="facile/recup", Z3="aerobie", Z4="tempo/soutenu", Z5="max"
INTERDIT: pourcentages bruts sans interpretation, markdown, langage de rapport
OBLIGATOIRE: Interprete les donnees en coaching actionnable. Rassure. Guide.

100% FRANCAIS uniquement."""


class DetailedAnalysisResponse(BaseModel):
    workout_id: str
    workout_name: str
    workout_date: str
    workout_type: str
    header: dict
    execution: dict
    meaning: dict
    recovery: dict
    advice: dict
    advanced: Optional[dict] = None


@api_router.get("/coach/detailed-analysis/{workout_id}")
async def get_detailed_analysis(workout_id: str, language: str = "en", user_id: str = "default"):
    """Get card-based detailed analysis for mobile view"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    # Get all workouts
    all_workouts = await db.workouts.find({}, {"_id": 0}).sort("date", -1).to_list(100)
    if not all_workouts:
        all_workouts = get_mock_workouts()
    
    # Find the workout
    workout = await db.workouts.find_one({"id": workout_id}, {"_id": 0})
    if not workout:
        workout = next((w for w in all_workouts if w["id"] == workout_id), None)
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Calculate baseline
    baseline = calculate_baseline_metrics(all_workouts, workout, days=14)
    
    # Build workout summary with enriched data
    workout_summary = {
        "type": workout.get("type"),
        "name": workout.get("name"),
        "date": workout.get("date"),
        "distance_km": workout.get("distance_km"),
        "duration_min": workout.get("duration_minutes"),
        "moving_time_min": workout.get("moving_time_minutes"),
        "avg_hr": workout.get("avg_heart_rate"),
        "max_hr": workout.get("max_heart_rate"),
        "hr_zones": workout.get("effort_zone_distribution"),
        "avg_pace_min_km": workout.get("avg_pace_min_km"),
        "best_pace_min_km": workout.get("best_pace_min_km"),
        "pace_variability": workout.get("pace_stats", {}).get("pace_variability") if workout.get("pace_stats") else None,
        "avg_cadence_spm": workout.get("avg_cadence_spm"),
        "avg_speed_kmh": workout.get("avg_speed_kmh"),
        "max_speed_kmh": workout.get("max_speed_kmh"),
        "elevation_m": workout.get("elevation_gain_m")
    }
    
    baseline_summary = {
        "sessions": baseline.get("workout_count", 0) if baseline else 0,
        "avg_distance": baseline.get("avg_distance_km") if baseline else None,
        "avg_duration": baseline.get("avg_duration_min") if baseline else None,
        "avg_hr": baseline.get("avg_heart_rate") if baseline else None,
        "avg_pace": baseline.get("avg_pace") if baseline else None,
        "avg_cadence": baseline.get("avg_cadence") if baseline else None
    } if baseline else {}
    
    # Generate AI analysis
    prompt_template = DETAILED_ANALYSIS_PROMPT_FR if language == "fr" else DETAILED_ANALYSIS_PROMPT_EN
    prompt = prompt_template.format(
        workout_data=workout_summary,
        baseline_data=baseline_summary
    )
    
    # Default response structure
    default_header = {
        "context": "Session analyzed." if language == "en" else "Séance analysée.",
        "session_name": workout.get("name", "Workout")
    }
    default_execution = {
        "intensity": "Moderate" if language == "en" else "Modérée",
        "volume": "Usual" if language == "en" else "Habituel",
        "regularity": "Stable"
    }
    default_meaning = {"text": ""}
    default_recovery = {"text": ""}
    default_advice = {"text": ""}
    default_advanced = {"comparisons": ""}
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"detailed_analysis_{workout_id}_{language}",
            system_message="You are a concise sports coach. Respond only in valid JSON."
        ).with_model("openai", "gpt-5.2")
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        # Parse JSON response
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        
        import json
        analysis_data = json.loads(response_clean.strip())
        
        header = analysis_data.get("header", default_header)
        execution = analysis_data.get("execution", default_execution)
        meaning = analysis_data.get("meaning", default_meaning)
        recovery = analysis_data.get("recovery", default_recovery)
        advice = analysis_data.get("advice", default_advice)
        advanced = analysis_data.get("advanced", default_advanced)
        
        logger.info(f"Detailed analysis generated for workout {workout_id} in {language}")
        
    except Exception as e:
        logger.error(f"Detailed analysis AI error: {e}")
        header = default_header
        execution = default_execution
        meaning = default_meaning
        recovery = default_recovery
        advice = default_advice
        advanced = default_advanced
    
    return DetailedAnalysisResponse(
        workout_id=workout_id,
        workout_name=workout.get("name", ""),
        workout_date=workout.get("date", ""),
        workout_type=workout.get("type", ""),
        header=header,
        execution=execution,
        meaning=meaning,
        recovery=recovery,
        advice=advice,
        advanced=advanced
    )


# ========== GARMIN INTEGRATION ENDPOINTS (DORMANT - NOT USER-FACING) ==========

@api_router.get("/garmin/status")
async def get_garmin_status(user_id: str = "default"):
    """Get Garmin connection status for a user (DORMANT)"""
    # Check if user has Garmin token
    token = await db.garmin_tokens.find_one({"user_id": user_id}, {"_id": 0})
    
    if not token:
        return GarminConnectionStatus(connected=False, last_sync=None, workout_count=0)
    
    # Get last sync time and workout count
    sync_info = await db.sync_history.find_one(
        {"user_id": user_id, "source": "garmin"},
        {"_id": 0},
        sort=[("synced_at", -1)]
    )
    
    workout_count = await db.workouts.count_documents({
        "data_source": "garmin"
    })
    
    return GarminConnectionStatus(
        connected=True,
        last_sync=sync_info.get("synced_at") if sync_info else None,
        workout_count=workout_count
    )


@api_router.get("/garmin/authorize")
async def garmin_authorize():
    """Initiate Garmin OAuth flow (DORMANT)"""
    if not GARMIN_CLIENT_ID or not GARMIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=503, 
            detail="Garmin integration not configured. Please add GARMIN_CLIENT_ID and GARMIN_CLIENT_SECRET to environment."
        )
    
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()
    
    # Store PKCE pair temporarily
    pkce_store[state] = code_verifier
    
    auth_url = get_garmin_auth_url(code_challenge, state)
    return {"authorization_url": auth_url, "state": state}


@api_router.get("/garmin/callback")
async def garmin_callback(code: str, state: str):
    """Handle Garmin OAuth callback (DORMANT)"""
    if state not in pkce_store:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    code_verifier = pkce_store.pop(state)
    
    try:
        # Exchange code for tokens
        token_data = await exchange_garmin_code(code, code_verifier)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        user_id = "default"  # In production, get from session
        
        # Store token
        await db.garmin_tokens.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                "created_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        logger.info(f"Garmin connected for user: {user_id}")
        
        # Redirect back to frontend settings
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?garmin=connected")
    
    except Exception as e:
        logger.error(f"Garmin OAuth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?garmin=error")


@api_router.post("/garmin/sync", response_model=GarminSyncResult)
async def sync_garmin_activities(user_id: str = "default"):
    """Sync activities from Garmin Connect (DORMANT)"""
    # Get token
    token = await db.garmin_tokens.find_one({"user_id": user_id}, {"_id": 0})
    
    if not token:
        return GarminSyncResult(success=False, synced_count=0, message="Not connected to Garmin")
    
    access_token = token.get("access_token")
    
    # Check if token is expired
    expires_at = token.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            return GarminSyncResult(success=False, synced_count=0, message="Token expired. Please reconnect.")
    
    try:
        # Fetch activities from Garmin
        activities = await fetch_garmin_activities(access_token)
        
        synced_count = 0
        for garmin_activity in activities:
            workout = convert_garmin_to_workout(garmin_activity)
            
            if workout:
                # Check if already exists
                existing = await db.workouts.find_one({"id": workout["id"]})
                if not existing:
                    await db.workouts.insert_one(workout)
                    synced_count += 1
        
        # Record sync history
        await db.sync_history.insert_one({
            "user_id": user_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "synced_count": synced_count,
            "source": "garmin"
        })
        
        logger.info(f"Garmin sync complete: {synced_count} workouts for user {user_id}")
        
        return GarminSyncResult(success=True, synced_count=synced_count, message=f"Synced {synced_count} workouts")
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Garmin API error: {e}")
        if e.response.status_code == 401:
            return GarminSyncResult(success=False, synced_count=0, message="Token expired. Please reconnect.")
        return GarminSyncResult(success=False, synced_count=0, message="Failed to fetch activities")
    except Exception as e:
        logger.error(f"Garmin sync error: {e}")
        return GarminSyncResult(success=False, synced_count=0, message="Sync failed")


@api_router.delete("/garmin/disconnect")
async def disconnect_garmin(user_id: str = "default"):
    """Disconnect Garmin account (DORMANT)"""
    await db.garmin_tokens.delete_one({"user_id": user_id})
    logger.info(f"Garmin disconnected for user: {user_id}")
    return {"success": True, "message": "Garmin disconnected"}


# ========== STRAVA INTEGRATION ENDPOINTS (ACTIVE) ==========

class StravaConnectionStatus(BaseModel):
    connected: bool
    last_sync: Optional[str] = None
    workout_count: int = 0


class StravaSyncResult(BaseModel):
    success: bool
    synced_count: int
    message: str


# Temporary storage for Strava OAuth state (in production, use Redis or DB)
strava_oauth_store: Dict[str, str] = {}


@api_router.get("/strava/status")
async def get_strava_status(user_id: str = "default"):
    """Get Strava connection status for a user"""
    # Check if user has Strava token
    token = await db.strava_tokens.find_one({"user_id": user_id}, {"_id": 0})
    
    if not token:
        return StravaConnectionStatus(connected=False, last_sync=None, workout_count=0)
    
    # Get last sync time
    sync_info = await db.sync_history.find_one(
        {"user_id": user_id, "source": "strava"},
        {"_id": 0},
        sort=[("synced_at", -1)]
    )
    
    # Count imported Strava workouts
    workout_count = await db.workouts.count_documents({
        "data_source": "strava"
    })
    
    return StravaConnectionStatus(
        connected=True,
        last_sync=sync_info.get("synced_at") if sync_info else None,
        workout_count=workout_count
    )


@api_router.get("/strava/authorize")
async def strava_authorize(user_id: str = "default"):
    """Initiate Strava OAuth flow"""
    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
        raise HTTPException(
            status_code=503, 
            detail="Data sync not configured. Please contact the administrator."
        )
    
    # Generate state for security
    state = secrets.token_urlsafe(32)
    
    # Store state with user_id for callback
    strava_oauth_store[state] = user_id
    
    # Build Strava authorization URL
    redirect_uri = STRAVA_REDIRECT_URI or f"{FRONTEND_URL}/settings"
    scope = "read,activity:read_all"
    
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
    )
    
    return {"authorization_url": auth_url, "state": state}


@api_router.get("/strava/callback")
async def strava_callback(code: str, state: str, scope: str = None):
    """Handle Strava OAuth callback"""
    if state not in strava_oauth_store:
        logger.warning(f"Invalid state parameter received: {state}")
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?strava=error&reason=invalid_state")
    
    user_id = strava_oauth_store.pop(state)
    
    try:
        # Exchange code for tokens
        token_data = await exchange_strava_code(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_at = token_data.get("expires_at")  # Strava returns Unix timestamp
        athlete_info = token_data.get("athlete", {})
        
        # Store token
        await db.strava_tokens.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "athlete_id": athlete_info.get("id"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        logger.info(f"Strava connected for user: {user_id}, athlete: {athlete_info.get('id')}")
        
        # Redirect back to frontend settings
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?strava=connected")
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava OAuth HTTP error: {e.response.status_code} - {e.response.text}")
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?strava=error&reason=token_exchange_failed")
    except Exception as e:
        logger.error(f"Strava OAuth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?strava=error&reason=unknown")


@api_router.post("/strava/sync", response_model=StravaSyncResult)
async def sync_strava_activities(user_id: str = "default", fetch_details: bool = True):
    """Sync activities from Strava with optional detailed HR/pace data"""
    # Get token
    token = await db.strava_tokens.find_one({"user_id": user_id}, {"_id": 0})
    
    if not token:
        return StravaSyncResult(success=False, synced_count=0, message="Not connected to Strava")
    
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    expires_at = token.get("expires_at")
    
    # Check if token is expired and refresh if needed
    if expires_at:
        if isinstance(expires_at, (int, float)):
            token_expired = expires_at < datetime.now(timezone.utc).timestamp()
        else:
            token_expired = False
            
        if token_expired and refresh_token:
            try:
                # Refresh the token
                new_token_data = await refresh_strava_token(refresh_token)
                access_token = new_token_data.get("access_token")
                
                # Update stored token
                await db.strava_tokens.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "access_token": new_token_data.get("access_token"),
                        "refresh_token": new_token_data.get("refresh_token"),
                        "expires_at": new_token_data.get("expires_at")
                    }}
                )
                logger.info(f"Strava token refreshed for user: {user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh Strava token: {e}")
                return StravaSyncResult(success=False, synced_count=0, message="Token expired. Please reconnect.")
    
    try:
        # Fetch activities from Strava
        activities = await fetch_strava_activities(access_token, per_page=100)
        
        synced_count = 0
        detailed_count = 0
        
        for idx, strava_activity in enumerate(activities):
            activity_id = strava_activity.get("id")
            
            # Fetch detailed streams for recent activities (first 30)
            streams_data = None
            zones_data = None
            
            if fetch_details and idx < 30 and activity_id:
                # Only fetch details for activities with HR data
                if strava_activity.get("has_heartrate") or strava_activity.get("average_heartrate"):
                    streams_data = await fetch_strava_activity_streams(access_token, str(activity_id))
                    zones_data = await fetch_strava_activity_zones(access_token, str(activity_id))
                    if streams_data or zones_data:
                        detailed_count += 1
            
            workout = convert_strava_to_workout(strava_activity, streams_data, zones_data)
            
            if workout:
                # Check if already exists
                existing = await db.workouts.find_one({"id": workout["id"]})
                if not existing:
                    await db.workouts.insert_one(workout)
                    synced_count += 1
                elif streams_data or zones_data:
                    # Update existing workout with detailed data
                    update_fields = {}
                    if workout.get("effort_zone_distribution"):
                        update_fields["effort_zone_distribution"] = workout["effort_zone_distribution"]
                    if workout.get("pace_stats"):
                        update_fields["pace_stats"] = workout["pace_stats"]
                    if workout.get("best_pace_min_km"):
                        update_fields["best_pace_min_km"] = workout["best_pace_min_km"]
                    if workout.get("avg_cadence_spm"):
                        update_fields["avg_cadence_spm"] = workout["avg_cadence_spm"]
                    
                    if update_fields:
                        await db.workouts.update_one(
                            {"id": workout["id"]},
                            {"$set": update_fields}
                        )
        
        # Record sync history
        await db.sync_history.insert_one({
            "user_id": user_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "synced_count": synced_count,
            "detailed_count": detailed_count,
            "source": "strava"
        })
        
        logger.info(f"Strava sync complete: {synced_count} new workouts, {detailed_count} with detailed data for user {user_id}")
        
        message = f"Synced {synced_count} workouts"
        if detailed_count > 0:
            message += f" ({detailed_count} with detailed HR/pace data)"
        
        return StravaSyncResult(success=True, synced_count=synced_count, message=message)
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava API error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            return StravaSyncResult(success=False, synced_count=0, message="Token expired. Please reconnect.")
        return StravaSyncResult(success=False, synced_count=0, message="Failed to fetch activities")
    except Exception as e:
        logger.error(f"Strava sync error: {e}")
        return StravaSyncResult(success=False, synced_count=0, message="Sync failed")


@api_router.delete("/strava/disconnect")
async def disconnect_strava(user_id: str = "default"):
    """Disconnect Strava account"""
    await db.strava_tokens.delete_one({"user_id": user_id})
    logger.info(f"Strava disconnected for user: {user_id}")
    return {"success": True, "message": "Strava disconnected"}


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
