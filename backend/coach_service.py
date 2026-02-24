"""
CardioCoach - Service de Coaching Cascade

Stratégie:
1. Analyse déterministe (instantanée, 0ms) via analysis_engine/rag_engine
2. Enrichissement LLM (GPT-4o-mini, ~500ms) si disponible
3. Fallback automatique vers déterministe si LLM échoue

Usage:
    from coach_service import analyze_workout, weekly_review, chat_response
"""

import logging
from typing import Dict, List, Optional, Tuple

from llm_coach import (
    enrich_chat_response,
    enrich_weekly_review,
    enrich_workout_analysis,
    LLM_MODEL
)
from chat_engine import generate_chat_response as generate_template_response

logger = logging.getLogger(__name__)


async def analyze_workout(
    workout: dict,
    rag_result: dict,
    user_id: str = "default"
) -> Tuple[str, bool]:
    """
    Analyse séance avec stratégie cascade.
    
    Args:
        workout: Données brutes de la séance
        rag_result: Résultat du RAG engine (analyse locale)
        user_id: ID utilisateur
        
    Returns:
        (summary_text, used_llm)
    """
    # 1. Analyse déterministe (déjà calculée par rag_engine)
    deterministic_summary = rag_result.get("summary", "")
    
    # 2. Enrichissement LLM
    try:
        workout_stats = {
            "distance_km": workout.get("distance_km", 0),
            "duree_min": workout.get("duration_minutes", 0),
            "allure": rag_result.get("pace_str", "N/A"),
            "fc_moy": workout.get("avg_heart_rate"),
            "fc_max": workout.get("max_heart_rate"),
            "denivele": workout.get("elevation_gain_m"),
            "type": workout.get("type"),
            "zones": workout.get("effort_zone_distribution", {}),
            "splits": rag_result.get("splits_analysis", {}),
            "comparison": rag_result.get("comparison", {}).get("progression", ""),
            "points_forts": rag_result.get("points_forts", []),
            "points_ameliorer": rag_result.get("points_ameliorer", []),
        }
        
        enriched, success, meta = await enrich_workout_analysis(
            workout=workout_stats,
            user_id=user_id
        )
        
        if success and enriched:
            logger.info(f"[Coach] ✅ Séance enrichie LLM en {meta.get('duration_sec', 0)}s")
            return enriched, True
            
    except Exception as e:
        logger.warning(f"[Coach] Séance fallback déterministe: {e}")
    
    return deterministic_summary, False


async def weekly_review(
    rag_result: dict,
    user_id: str = "default"
) -> Tuple[str, bool]:
    """
    Bilan hebdomadaire avec stratégie cascade.
    
    Args:
        rag_result: Résultat du RAG engine (analyse locale)
        user_id: ID utilisateur
        
    Returns:
        (summary_text, used_llm)
    """
    # 1. Bilan déterministe (déjà calculé par rag_engine)
    deterministic_summary = rag_result.get("summary", "")
    
    # 2. Enrichissement LLM
    try:
        weekly_stats = {
            "km_semaine": rag_result["metrics"].get("km_total", 0),
            "nb_seances": rag_result["metrics"].get("nb_seances", 0),
            "allure_moy": rag_result["metrics"].get("allure_moyenne", "N/A"),
            "cadence_moy": rag_result["metrics"].get("cadence_moyenne", 0),
            "zones": rag_result["metrics"].get("zones", {}),
            "ratio_charge": rag_result["metrics"].get("ratio", 1.0),
            "points_forts": rag_result.get("points_forts", []),
            "points_ameliorer": rag_result.get("points_ameliorer", []),
            "tendance": rag_result["comparison"].get("evolution", "stable"),
        }
        
        enriched, success, meta = await enrich_weekly_review(
            stats=weekly_stats,
            user_id=user_id
        )
        
        if success and enriched:
            logger.info(f"[Coach] ✅ Bilan enrichi LLM en {meta.get('duration_sec', 0)}s")
            return enriched, True
            
    except Exception as e:
        logger.warning(f"[Coach] Bilan fallback déterministe: {e}")
    
    return deterministic_summary, False


async def chat_response(
    message: str,
    context: dict,
    history: List[dict],
    user_id: str,
    workouts: List[dict] = None,
    user_goal: dict = None
) -> Tuple[str, bool, dict]:
    """
    Réponse chat avec stratégie cascade.
    
    Args:
        message: Message utilisateur
        context: Contexte d'entraînement
        history: Historique de conversation
        user_id: ID utilisateur
        workouts: Liste des séances (pour fallback)
        user_goal: Objectif utilisateur (pour fallback)
        
    Returns:
        (response_text, used_llm, metadata)
    """
    metadata = {}
    
    # 1. Essayer LLM d'abord (meilleure qualité)
    try:
        response, success, meta = await enrich_chat_response(
            user_message=message,
            context=context,
            conversation_history=history,
            user_id=user_id
        )
        
        if success and response:
            logger.info(f"[Coach] ✅ Chat LLM ({LLM_MODEL}) en {meta.get('duration_sec', 0)}s")
            metadata = meta
            return response, True, metadata
            
    except Exception as e:
        logger.warning(f"[Coach] Chat fallback templates: {e}")
    
    # 2. Fallback vers templates Python
    logger.info(f"[Coach] Chat fallback déterministe")
    
    try:
        result = await generate_template_response(
            message=message,
            user_id=user_id,
            workouts=workouts or [],
            user_goal=user_goal
        )
        
        if isinstance(result, dict):
            return result.get("response", ""), False, {"suggestions": result.get("suggestions", [])}
        return result, False, {}
        
    except Exception as e:
        logger.error(f"[Coach] Erreur fallback templates: {e}")
        return "Désolé, je n'ai pas pu traiter ta demande. Réessaie.", False, {}


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "analyze_workout",
    "weekly_review", 
    "chat_response"
]
