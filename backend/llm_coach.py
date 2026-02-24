"""
CardioCoach - Module LLM Coach (GPT-4o-mini)

Ce module gère l'enrichissement des textes coach via GPT-4o-mini.
Les données d'entraînement sont envoyées directement au LLM pour
générer des analyses personnalisées et motivantes.

Flux:
1. Réception des données d'entraînement
2. Envoi à GPT-4o-mini pour génération texte
3. Fallback templates Python si erreur
"""

import os
import time
import json
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
LLM_MODEL = "gpt-4.1-mini"
LLM_PROVIDER = "openai"
LLM_TIMEOUT = 15

# ============================================================
# PROMPTS SYSTÈME
# ============================================================

SYSTEM_PROMPT_COACH = """Tu es un coach running expérimenté, empathique et précis. 
Réponds toujours en français courant avec contractions ('t'as', 'c'est', 'j'te').

Structure de réponse :
1. Positif d'abord (félicite, encourage)
2. Analyse claire et simple des données (explique les chiffres sans jargon)
3. Conseil actionable (allure, cadence, récup, renforcement)
4. Question de relance si pertinent

Focus : allure/km, cadence, zones cardio, récupération, fatigue, plans.
Sois concret, motivant et bienveillant. Max 4-5 phrases."""

SYSTEM_PROMPT_BILAN = """Tu es un coach running qui fait le bilan hebdomadaire.
Réponds en français courant avec contractions ('t'as', 'c'est').

Structure du bilan :
1. Intro positive (félicite la régularité ou l'effort)
2. Analyse des chiffres clés (explique simplement)
3. Points forts (2 max)
4. Point à améliorer (1 max, formulé positivement)
5. Conseil pour la semaine prochaine
6. Question de relance motivante

Sois encourageant même si les stats sont moyennes. Max 6-8 phrases."""

SYSTEM_PROMPT_SEANCE = """Tu es un coach running qui analyse une séance.
Réponds en français courant avec contractions ('t'as', 'c'est').

Structure :
1. Réaction positive sur l'effort accompli
2. Analyse simple des données (allure, FC, régularité)
3. Point fort de la séance
4. Conseil pour la prochaine sortie
5. Relance motivante (optionnel)

Sois concret et encourageant. Max 4-5 phrases."""

SYSTEM_PROMPT_PLAN = """Tu es un coach running expert élite spécialisé en périodisation.
Répond UNIQUEMENT en JSON valide, sans texte avant ou après."""


# ============================================================
# FONCTIONS D'ENRICHISSEMENT
# ============================================================

async def enrich_chat_response(
    user_message: str,
    context: Dict,
    conversation_history: List[Dict],
    user_id: str = "unknown"
) -> Tuple[Optional[str], bool, Dict]:
    """Enrichit la réponse chat avec GPT-4o-mini."""
    prompt = f"""DONNÉES UTILISATEUR:
{_format_context(context)}

HISTORIQUE CONVERSATION:
{_format_history(conversation_history)}

QUESTION: {user_message}

Réponds en tant que coach running motivant."""

    return await _call_gpt(SYSTEM_PROMPT_COACH, prompt, user_id, "chat")


async def enrich_weekly_review(
    stats: Dict,
    user_id: str = "unknown"
) -> Tuple[Optional[str], bool, Dict]:
    """Enrichit le bilan hebdomadaire avec GPT-4o-mini."""
    prompt = f"""STATS SEMAINE:
{_format_context(stats)}

Génère un bilan hebdomadaire motivant et personnalisé basé sur ces données."""

    return await _call_gpt(SYSTEM_PROMPT_BILAN, prompt, user_id, "bilan")


async def enrich_workout_analysis(
    workout: Dict,
    user_id: str = "unknown"
) -> Tuple[Optional[str], bool, Dict]:
    """Enrichit l'analyse d'une séance avec GPT-4o-mini."""
    prompt = f"""DONNÉES SÉANCE:
{_format_context(workout)}

Analyse cette séance en tant que coach running bienveillant."""

    return await _call_gpt(SYSTEM_PROMPT_SEANCE, prompt, user_id, "seance")


async def generate_cycle_week(
    context: Dict,
    phase: str,
    target_load: int,
    goal: str,
    user_id: str = "unknown"
) -> Tuple[Optional[Dict], bool, Dict]:
    """
    Génère un plan de semaine d'entraînement structuré.
    
    Args:
        context: Données de fitness (CTL, ATL, TSB, ACWR, weekly_km)
        phase: Phase actuelle (build, deload, intensification, taper, race)
        target_load: Charge cible en TSS
        goal: Objectif (5K, 10K, SEMI, MARATHON, ULTRA)
        user_id: ID utilisateur
        
    Returns:
        (plan_dict, success, metadata)
    """
    prompt = f"""Tu es un coach running expert élite.

Objectif : {goal}
Phase : {phase}
Charge cible : {target_load}

Données athlète :
CTL: {context.get('ctl', 40)}
ATL: {context.get('atl', 45)}
TSB: {context.get('tsb', -5)}
ACWR: {round(context.get('acwr', 1.0), 2)}
Volume hebdo: {context.get('weekly_km', 30)} km

Règles :
- Respecte progressivité (max +10% volume/semaine)
- Ajuste long run selon objectif
- Marathon = sortie longue prioritaire (30-35% du volume)
- Semi = tempo et seuil (20-25% intensité)
- 10K = VMA et seuil (25-30% intensité)
- 5K = VMA et vitesse (30% intensité)
- Si ACWR > 1.3 : réduire la charge
- Si TSB < -20 : ajouter repos

Répond UNIQUEMENT en JSON valide :

{{
  "focus": "{phase}",
  "planned_load": {target_load},
  "weekly_km": 0,
  "sessions": [
    {{
      "day": "Lundi",
      "type": "Repos",
      "duration": "0min",
      "details": "Récupération complète",
      "intensity": "rest",
      "estimated_tss": 0
    }},
    {{
      "day": "Mardi",
      "type": "Endurance",
      "duration": "45min",
      "details": "Footing facile en zone 2",
      "intensity": "easy",
      "estimated_tss": 45
    }},
    {{
      "day": "Mercredi",
      "type": "Fractionné",
      "duration": "50min",
      "details": "10x400m à allure 5K, récup 1min30",
      "intensity": "hard",
      "estimated_tss": 70
    }},
    {{
      "day": "Jeudi",
      "type": "Récupération",
      "duration": "30min",
      "details": "Footing très léger",
      "intensity": "easy",
      "estimated_tss": 25
    }},
    {{
      "day": "Vendredi",
      "type": "Repos",
      "duration": "0min",
      "details": "Récupération ou cross-training léger",
      "intensity": "rest",
      "estimated_tss": 0
    }},
    {{
      "day": "Samedi",
      "type": "Tempo",
      "duration": "40min",
      "details": "20min à allure semi-marathon",
      "intensity": "moderate",
      "estimated_tss": 55
    }},
    {{
      "day": "Dimanche",
      "type": "Sortie longue",
      "duration": "90min",
      "details": "Sortie longue progressive, derniers 20min à allure marathon",
      "intensity": "moderate",
      "estimated_tss": 100
    }}
  ],
  "advice": "Conseil personnalisé pour la semaine"
}}"""

    start_time = time.time()
    metadata = {
        "model": LLM_MODEL,
        "provider": LLM_PROVIDER,
        "context_type": "cycle_week",
        "duration_sec": 0,
        "success": False
    }
    
    if not EMERGENT_LLM_KEY or not EMERGENT_LLM_KEY.startswith("sk-emergent"):
        logger.warning("[LLM] Emergent LLM Key non configurée")
        return None, False, metadata
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        session_id = f"cardiocoach_plan_{user_id}_{int(time.time())}"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=SYSTEM_PROMPT_PLAN
        ).with_model(LLM_PROVIDER, LLM_MODEL)
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=LLM_TIMEOUT
        )
        
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        
        # Parser le JSON
        response_text = str(response).strip()
        
        # Nettoyer si markdown
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        plan = json.loads(response_text)
        
        # Calculer le volume total
        total_tss = sum(s.get("estimated_tss", 0) for s in plan.get("sessions", []))
        plan["total_tss"] = total_tss
        
        metadata["success"] = True
        logger.info(f"[LLM] ✅ Plan semaine généré en {elapsed:.2f}s (TSS: {total_tss})")
        
        return plan, True, metadata
        
    except json.JSONDecodeError as e:
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        logger.error(f"[LLM] ❌ Erreur parsing JSON: {e}")
        return None, False, metadata
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        logger.warning(f"[LLM] ⏱️ Timeout plan après {elapsed:.2f}s")
        return None, False, metadata
        
    except Exception as e:
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        logger.error(f"[LLM] ❌ Erreur plan: {e}")
        return None, False, metadata


# ============================================================
# FONCTIONS INTERNES
# ============================================================

async def _call_gpt(
    system_prompt: str,
    user_prompt: str,
    user_id: str,
    context_type: str
) -> Tuple[Optional[str], bool, Dict]:
    """Appel GPT-4o-mini via Emergent LLM Key"""
    
    start_time = time.time()
    metadata = {
        "model": LLM_MODEL,
        "provider": LLM_PROVIDER,
        "context_type": context_type,
        "duration_sec": 0,
        "success": False
    }
    
    if not EMERGENT_LLM_KEY or not EMERGENT_LLM_KEY.startswith("sk-emergent"):
        logger.warning("[LLM] Emergent LLM Key non configurée")
        return None, False, metadata
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        session_id = f"cardiocoach_{context_type}_{user_id}_{int(time.time())}"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_prompt
        ).with_model(LLM_PROVIDER, LLM_MODEL)
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=user_prompt)),
            timeout=LLM_TIMEOUT
        )
        
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        metadata["success"] = True
        
        response_text = _clean_response(str(response))
        
        if response_text:
            logger.info(f"[LLM] ✅ {context_type} enrichi en {elapsed:.2f}s")
            return response_text, True, metadata
        else:
            logger.warning(f"[LLM] Réponse vide pour {context_type}")
            return None, False, metadata
            
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        logger.warning(f"[LLM] ⏱️ Timeout après {elapsed:.2f}s")
        return None, False, metadata
        
    except Exception as e:
        elapsed = time.time() - start_time
        metadata["duration_sec"] = round(elapsed, 2)
        logger.error(f"[LLM] ❌ Erreur: {e}")
        return None, False, metadata


def _format_context(data: Dict) -> str:
    """Formate les données en texte lisible pour le LLM"""
    lines = []
    for key, value in data.items():
        if value is not None and value != "" and value != {} and value != []:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "Aucune donnée"


def _format_history(history: List[Dict]) -> str:
    """Formate l'historique de conversation"""
    if not history:
        return "Début de conversation"
    
    lines = []
    for msg in history[-4:]:
        role = "User" if msg.get("role") == "user" else "Coach"
        content = msg.get("content", "")[:150]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _clean_response(response: str) -> str:
    """Nettoie la réponse GPT"""
    if not response:
        return ""
    
    response = response.strip()
    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1]
    
    if len(response) > 700:
        response = response[:700]
        last_period = max(response.rfind("."), response.rfind("!"), response.rfind("?"))
        if last_period > 400:
            response = response[:last_period + 1]
    
    return response.strip()


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "enrich_chat_response",
    "enrich_weekly_review", 
    "enrich_workout_analysis",
    "generate_cycle_week",
    "LLM_MODEL",
    "LLM_PROVIDER"
]
