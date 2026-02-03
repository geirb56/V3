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
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM API Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

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


async def fetch_strava_activities(access_token: str, per_page: int = 100) -> list:
    """Fetch activities from Strava API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"per_page": per_page, "page": 1}
        )
        response.raise_for_status()
        return response.json()


def convert_strava_to_workout(strava_activity: dict) -> dict:
    """Convert Strava activity to CardioCoach workout format"""
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
    distance = strava_activity.get("distance", 0)  # in meters
    avg_hr = strava_activity.get("average_heartrate")
    max_hr = strava_activity.get("max_heartrate")
    elevation = strava_activity.get("total_elevation_gain")
    calories = strava_activity.get("calories")
    avg_speed = strava_activity.get("average_speed", 0)  # in m/s
    
    # Calculate pace (for runs) or speed (for rides)
    avg_pace_min_km = None
    avg_speed_kmh = None
    
    if avg_speed and avg_speed > 0:
        if workout_type == "run":
            # Convert m/s to min/km
            speed_km_per_min = (avg_speed * 60) / 1000
            if speed_km_per_min > 0:
                avg_pace_min_km = round(1 / speed_km_per_min, 2)
        else:
            # Convert m/s to km/h
            avg_speed_kmh = round(avg_speed * 3.6, 1)
    
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
        "distance_km": round(distance / 1000, 2) if distance else 0,
        "data_source": "strava",
        "strava_activity_id": str(strava_activity.get("id")),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add optional fields only if present (graceful handling)
    if avg_hr:
        workout["avg_heart_rate"] = int(avg_hr)
    if max_hr:
        workout["max_heart_rate"] = int(max_hr)
    if avg_pace_min_km:
        workout["avg_pace_min_km"] = avg_pace_min_km
    if avg_speed_kmh:
        workout["avg_speed_kmh"] = avg_speed_kmh
    if calories:
        workout["calories"] = int(calories)
    if elevation:
        workout["elevation_gain_m"] = int(elevation)
    
    return workout


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
            "data_source": "manual",
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
            "data_source": "manual",
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
            "data_source": "manual",
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
            "data_source": "manual",
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
            "data_source": "manual",
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
            "data_source": "manual",
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
            "data_source": "manual",
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
            detail="Strava integration not configured. Please contact the administrator."
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
async def sync_strava_activities(user_id: str = "default"):
    """Sync activities from Strava"""
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
        for strava_activity in activities:
            workout = convert_strava_to_workout(strava_activity)
            
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
            "source": "strava"
        })
        
        logger.info(f"Strava sync complete: {synced_count} workouts for user {user_id}")
        
        return StravaSyncResult(success=True, synced_count=synced_count, message=f"Synced {synced_count} workouts")
    
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
