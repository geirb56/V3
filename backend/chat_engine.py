"""
CardioCoach Chat Engine
100% Backend Python - NO LLM, NO External API
Rule-based responses with templates and randomization
"""

import random
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta


# ============================================================
# KEYWORD DETECTION PATTERNS
# ============================================================

KEYWORD_PATTERNS = {
    "fatigue": [
        r"fatigu[ée]?", r"crev[ée]?", r"épuis[ée]?", r"lourd", r"jambes? lourdes?",
        r"décroch", r"plus dur", r"difficile", r"mal aux jambes", r"courbatur",
        r"vidé", r"cassé", r"mort", r"crampe", r"plus de jus"
    ],
    "allure": [
        r"allure", r"pace", r"vitesse", r"tempo", r"rythme", r"min/?km",
        r"plus vite", r"lent", r"rapide", r"accélérer", r"ralentir"
    ],
    "cadence": [
        r"cadence", r"pas/?min", r"spm", r"foulée", r"freq", r"pas par"
    ],
    "recuperation": [
        r"récup", r"repos", r"off", r"jour de repos", r"récupér", r"recharger",
        r"dormir", r"sommeil", r"massage", r"étirement"
    ],
    "plan": [
        r"plan", r"programme", r"semaine prochaine", r"prochaine sortie",
        r"demain", r"prévoir", r"planifier", r"organiser", r"structure"
    ],
    "blessure": [
        r"bless", r"douleur", r"mal à", r"tendon", r"genou", r"cheville",
        r"hanche", r"mollet", r"tibia", r"périoste", r"aponévrose"
    ],
    "objectif": [
        r"objectif", r"course", r"marathon", r"semi", r"10k", r"trail",
        r"compétition", r"dossard", r"chrono", r"record"
    ],
    "zones": [
        r"zone", r"z[1-5]", r"fc", r"cardiaque", r"fréquence", r"bpm",
        r"intensité", r"seuil", r"aérobie", r"vo2"
    ],
    "semaine": [
        r"semaine", r"cette semaine", r"7 jours", r"bilan", r"résumé",
        r"analyse", r"mes séances", r"mon entraînement"
    ],
    "pourquoi": [
        r"pourquoi", r"comment", r"expliqu", r"raison", r"cause", r"normal"
    ]
}


# ============================================================
# RESPONSE TEMPLATES BY CATEGORY
# ============================================================

TEMPLATES = {
    "fatigue": [
        "Ton allure a décroché de {decrochage_pct}% en fin de sortie avec une FC qui monte → fatigue accumulée. Priorise une sortie très facile Z1-Z2 demain pour absorber. Tu as senti tes jambes lourdes dès le début ou seulement à la fin ?",
        
        "Ratio charge aiguë/chronique à {ratio_charge:.1f}, c'est au-dessus de l'idéal (0.8-1.3) → signe de surcharge. Repos ou footing zen recommandé. Hydratation et sommeil au top cette semaine ?",
        
        "Avec {km_semaine} km cette semaine et {pct_z4_z5}% en zones hautes, le corps demande du repos. Demain : récup active ou off complet. Tu ressens cette fatigue depuis combien de jours ?",
        
        "La fatigue que tu décris est normale après {nb_seances} séances soutenues. Le corps progresse au repos, pas à l'effort ! Prévois 1-2 jours faciles. Comment tu dors en ce moment ?",
        
        "Symptôme classique de surcharge : jambes lourdes + allure qui décroche. Ta charge récente ({charge_acute} vs {charge_chronic} habituel) confirme. Réduis de 30% cette semaine pour repartir frais."
    ],
    
    "allure": [
        "Ton allure moyenne actuelle est {allure_moy}/km. Pour un tempo efficace, vise {allure_tempo}/km (15-20 s/km plus rapide). Sur tes sorties faciles, reste autour de {allure_easy}/km. Tu cours souvent sur terrain plat ou vallonné ?",
        
        "Allure stable à {allure_moy}/km ces dernières semaines, bravo la régularité ! Pour progresser, ajoute 1 sortie seuil à {allure_seuil}/km par semaine. Ça représente environ 10% de ton volume. Tu as essayé le fractionné récemment ?",
        
        "Avec ton objectif à {objectif_allure}/km, ton allure actuelle ({allure_moy}/km) est {ecart_allure}. Continue le travail spécifique : 1 séance tempo + 1 sortie longue par semaine. Quel est ton prochain objectif course ?",
        
        "Pour améliorer ton allure, la clé c'est la régularité en Z2 (80% du temps) + travail spécifique (20%). Tu fais combien de séances par semaine en moyenne ?"
    ],
    
    "cadence": [
        "Ta cadence moyenne est {cadence_moy} spm. L'idéal pour l'économie de course : 170-180 spm. Essaie de monter à {cadence_cible} spm sur les portions soutenues en raccourcissant ta foulée. Tu utilises un métronome parfois ?",
        
        "Cadence à {cadence_moy} spm → un peu basse. Vise {cadence_cible} spm pour gagner en efficacité et réduire l'impact au sol. Astuce : écoute une playlist à 170-180 BPM. Ça change tout ! Tu as déjà essayé ?",
        
        "Bonne cadence à {cadence_moy} spm ! Tu es dans la zone optimale. Maintenant, travaille la régularité : même cadence en montée qu'en plat (en adaptant la foulée). Ton terrain habituel est plutôt plat ou vallonné ?"
    ],
    
    "recuperation": [
        "Score récup estimé : {score_recup}/100 → {niveau_recup}. {conseil_recup} Tu as bien dormi cette semaine ?",
        
        "Après ta charge récente ({km_semaine} km, {pct_z4_z5}% intense), une journée off ou footing très facile serait idéale. Le corps progresse au repos ! Tu prévois quoi demain ?",
        
        "La récupération fait partie de l'entraînement. Avec {nb_seances} séances cette semaine, une pause active (marche, vélo tranquille) aiderait. Tu intègres des étirements ou du renforcement ?",
        
        "Charge élevée détectée mais récup correcte. Demain : Z2 tranquille 40-50 min max pour recharger. Écoute ton corps, pas ton ego ! Comment tu te sens au réveil ces derniers jours ?"
    ],
    
    "plan": [
        "Pour ta semaine prochaine, je te propose {volume_cible} km avec 70-80% en Z2 (facile) et 1 séance spécifique à {allure_specifique}/km. Demain : {sortie_demain}. Objectif toujours le {date_objectif} ?",
        
        "Plan suggéré : {nb_seances_cible} séances cette semaine. Mix idéal : 2 sorties endurance + 1 sortie qualité (tempo ou fractionné). Volume visé : {volume_cible} km. Ça te semble jouable ?",
        
        "Pour progresser vers ton objectif, la semaine type : Lundi repos, Mardi {seance_mardi}, Jeudi {seance_jeudi}, Samedi ou Dimanche {seance_weekend}. Tu préfères courir en semaine ou le weekend ?",
        
        "Prochaine sortie conseillée : {sortie_conseillee}. Focus sur {focus_seance}. Après ça, tu auras fait {km_projetes} km sur la semaine. Un bon équilibre ! Tu as une préférence matin ou soir ?"
    ],
    
    "blessure": [
        "⚠️ Attention aux signaux du corps ! Si tu ressens une douleur {type_douleur}, arrête et consulte. En attendant : repos, glace, compression. La douleur est là depuis combien de temps ?",
        
        "Les douleurs aux {zone_corps} arrivent souvent avec une montée en charge trop rapide. Règle d'or : pas plus de 10% de volume en plus par semaine. Tu as augmenté récemment ?",
        
        "Si c'est une douleur musculaire (courbature), c'est normal après l'effort. Si c'est articulaire ou tendineux, prudence ! Décris-moi plus précisément : c'est où et quand ça fait mal ?"
    ],
    
    "objectif": [
        "Objectif {nom_objectif} dans {jours_restants} jours ! Avec ton niveau actuel ({allure_moy}/km), tu peux viser {temps_estime}. On reste sur le plan ou tu veux ajuster quelque chose ?",
        
        "Pour ton {nom_objectif}, il te reste {semaines_restantes} semaines de préparation. Les 3 dernières semaines : réduction progressive de la charge (-20%, -40%, affûtage). Tu te sens prêt(e) ?",
        
        "Ton allure cible pour {nom_objectif} est {allure_cible}/km. Tu tournes actuellement à {allure_moy}/km, c'est {commentaire_ecart}. Continue le travail spécifique ! Tu as prévu une sortie de répétition sur le parcours ?"
    ],
    
    "zones": [
        "Ta répartition actuelle : {pct_z1_z2}% en Z1-Z2 (facile), {pct_z3}% en Z3 (tempo), {pct_z4_z5}% en Z4-Z5 (dur). L'idéal c'est 80/20 (facile/dur). {conseil_zones} Tu veux que je t'explique les zones ?",
        
        "Zone 2 = endurance fondamentale = la base de tout. Tu y passes {pct_z2}% de ton temps. Pour progresser, augmente ce pourcentage à 60-70% minimum. Tes sorties faciles sont vraiment faciles ?",
        
        "Zones hautes ({pct_z4_z5}%) : c'est ton travail de qualité, efficace mais coûteux. Max 20% du volume total. Tu es à {statut_zones}. Comment tu gères l'intensité sur tes sorties ?"
    ],
    
    "semaine": [
        "Ta semaine : {km_semaine} km sur {nb_seances} séances, allure moyenne {allure_moy}/km. Points forts : {point_fort}. À surveiller : {point_ameliorer}. Tu veux un plan adapté pour la semaine prochaine ?",
        
        "Bilan : {km_semaine} km, charge {charge_semaine}, {pct_z2}% en endurance. C'est {appreciation_semaine}. Pour la suite : {conseil_semaine}. Comment tu te sens globalement ?",
        
        "Cette semaine : {nb_seances} séances pour {km_semaine} km ({variation_volume}% vs semaine dernière). Intensité {niveau_intensite}. Régularité {niveau_regularite}. Quel est ton ressenti ?"
    ],
    
    "pourquoi": [
        "Bonne question ! {explication} C'est un principe fondamental de l'entraînement. Tu veux que je développe ?",
        
        "{reponse_pourquoi} La clé c'est l'équilibre charge/récup. D'autres questions ?",
        
        "L'explication : {explication_detaillee}. En pratique, ça veut dire {conseil_pratique}. C'est plus clair ?"
    ],
    
    "fallback": [
        "Je n'ai pas tout compris, peux-tu préciser ? Parle-moi de ta fatigue, allure, cadence, récup ou plan. Je suis là pour t'aider !",
        
        "Hmm, reformule ta question autrement ? Je peux t'aider sur : fatigue, allure, cadence, récupération, plan d'entraînement, zones cardiaques...",
        
        "Je ne suis pas sûr de comprendre. Tu veux qu'on parle de ta forme actuelle ? De ton prochain objectif ? De ta récup ? Dis-moi !"
    ]
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def detect_category(message: str) -> str:
    """Detect the main category of the user's question"""
    message_lower = message.lower()
    
    # Check each category's patterns
    scores = {}
    for category, patterns in KEYWORD_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, message_lower):
                score += 1
        if score > 0:
            scores[category] = score
    
    if not scores:
        return "fallback"
    
    # Return category with highest score
    return max(scores, key=scores.get)


def calculate_training_metrics(workouts: List[dict], user_goal: dict = None) -> dict:
    """Calculate all metrics needed for chat responses"""
    
    # Default values
    metrics = {
        "km_semaine": 0,
        "nb_seances": 0,
        "allure_moy": "6:00",
        "cadence_moy": 170,
        "pct_z1_z2": 60,
        "pct_z3": 20,
        "pct_z4_z5": 20,
        "pct_z2": 40,
        "charge_acute": 30,
        "charge_chronic": 25,
        "ratio_charge": 1.0,
        "score_recup": 70,
        "niveau_recup": "correct",
        "decrochage_pct": 5,
        "variation_volume": 0,
        "niveau_intensite": "modérée",
        "niveau_regularite": "bonne",
        "point_fort": "régularité",
        "point_ameliorer": "intensité",
        "appreciation_semaine": "équilibrée",
        "conseil_semaine": "continue comme ça"
    }
    
    if not workouts:
        return metrics
    
    # Calculate basic metrics
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    
    week_workouts = []
    for w in workouts:
        try:
            w_date = datetime.fromisoformat(w["date"].replace("Z", "+00:00"))
            if w_date >= week_start:
                week_workouts.append(w)
        except:
            continue
    
    metrics["nb_seances"] = len(week_workouts)
    metrics["km_semaine"] = round(sum(w.get("distance_km", 0) or 0 for w in week_workouts), 1)
    
    # Average pace
    paces = [w.get("avg_pace_min_km") for w in week_workouts if w.get("avg_pace_min_km")]
    if paces:
        avg_pace = sum(paces) / len(paces)
        mins = int(avg_pace)
        secs = int((avg_pace - mins) * 60)
        metrics["allure_moy"] = f"{mins}:{secs:02d}"
    
    # Average cadence
    cadences = [w.get("avg_cadence_spm") for w in week_workouts if w.get("avg_cadence_spm")]
    if cadences:
        metrics["cadence_moy"] = round(sum(cadences) / len(cadences))
    
    # Zone distribution
    zone_totals = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
    zone_count = 0
    for w in week_workouts:
        zones = w.get("effort_zone_distribution", {})
        if zones:
            for z in zone_totals:
                zone_totals[z] += zones.get(z, 0) or 0
            zone_count += 1
    
    if zone_count > 0:
        avg_zones = {z: v / zone_count for z, v in zone_totals.items()}
        metrics["pct_z1_z2"] = round(avg_zones["z1"] + avg_zones["z2"])
        metrics["pct_z3"] = round(avg_zones["z3"])
        metrics["pct_z4_z5"] = round(avg_zones["z4"] + avg_zones["z5"])
        metrics["pct_z2"] = round(avg_zones["z2"])
    
    # Training load (simplified acute/chronic)
    metrics["charge_acute"] = round(metrics["km_semaine"] * (1 + metrics["pct_z4_z5"] / 100))
    
    # Calculate chronic load from older workouts
    chronic_start = now - timedelta(days=28)
    chronic_workouts = [w for w in workouts if 
                       chronic_start <= datetime.fromisoformat(w.get("date", "2000-01-01").replace("Z", "+00:00")) < week_start]
    chronic_km = sum(w.get("distance_km", 0) or 0 for w in chronic_workouts) / 3  # Average per week
    metrics["charge_chronic"] = round(chronic_km * 1.1) or 20
    
    # Ratio
    if metrics["charge_chronic"] > 0:
        metrics["ratio_charge"] = round(metrics["charge_acute"] / metrics["charge_chronic"], 2)
    
    # Recovery score (simplified)
    if metrics["ratio_charge"] > 1.5:
        metrics["score_recup"] = 40
        metrics["niveau_recup"] = "faible"
    elif metrics["ratio_charge"] > 1.2:
        metrics["score_recup"] = 60
        metrics["niveau_recup"] = "correct"
    else:
        metrics["score_recup"] = 80
        metrics["niveau_recup"] = "bon"
    
    # Training quality assessment
    if metrics["pct_z4_z5"] > 30:
        metrics["niveau_intensite"] = "élevée"
        metrics["point_ameliorer"] = "récupération"
    elif metrics["pct_z4_z5"] < 10:
        metrics["niveau_intensite"] = "basse"
        metrics["point_ameliorer"] = "travail spécifique"
    
    if metrics["nb_seances"] >= 4:
        metrics["niveau_regularite"] = "excellente"
        metrics["point_fort"] = "constance"
    elif metrics["nb_seances"] >= 3:
        metrics["niveau_regularite"] = "bonne"
    else:
        metrics["niveau_regularite"] = "à améliorer"
        metrics["point_ameliorer"] = "régularité"
    
    # Volume variation
    prev_week_start = week_start - timedelta(days=7)
    prev_workouts = [w for w in workouts if 
                   prev_week_start <= datetime.fromisoformat(w.get("date", "2000-01-01").replace("Z", "+00:00")) < week_start]
    prev_km = sum(w.get("distance_km", 0) or 0 for w in prev_workouts)
    if prev_km > 0:
        metrics["variation_volume"] = round((metrics["km_semaine"] - prev_km) / prev_km * 100)
    
    # Goal-related metrics
    if user_goal:
        metrics["nom_objectif"] = user_goal.get("event_name", "ta course")
        metrics["allure_cible"] = user_goal.get("target_pace", "5:30")
        try:
            event_date = datetime.fromisoformat(user_goal["event_date"])
            days = (event_date.date() - now.date()).days
            metrics["jours_restants"] = max(0, days)
            metrics["semaines_restantes"] = max(0, days // 7)
            metrics["date_objectif"] = event_date.strftime("%d/%m")
        except:
            metrics["jours_restants"] = 30
            metrics["date_objectif"] = "ton objectif"
    
    return metrics


def calculate_derived_metrics(base_metrics: dict) -> dict:
    """Calculate derived metrics like target paces, cadences, etc."""
    
    metrics = base_metrics.copy()
    
    # Parse current pace to calculate targets
    try:
        parts = metrics["allure_moy"].split(":")
        pace_seconds = int(parts[0]) * 60 + int(parts[1])
        
        # Tempo pace (15-20s faster)
        tempo_secs = pace_seconds - 18
        metrics["allure_tempo"] = f"{tempo_secs // 60}:{tempo_secs % 60:02d}"
        
        # Seuil pace (25-30s faster)
        seuil_secs = pace_seconds - 28
        metrics["allure_seuil"] = f"{seuil_secs // 60}:{seuil_secs % 60:02d}"
        
        # Easy pace (20-30s slower)
        easy_secs = pace_seconds + 25
        metrics["allure_easy"] = f"{easy_secs // 60}:{easy_secs % 60:02d}"
        
        # Specific pace for goal
        metrics["allure_specifique"] = metrics.get("allure_cible", metrics["allure_tempo"])
        
    except:
        metrics["allure_tempo"] = "5:30"
        metrics["allure_seuil"] = "5:15"
        metrics["allure_easy"] = "6:30"
        metrics["allure_specifique"] = "5:30"
    
    # Target cadence
    metrics["cadence_cible"] = max(175, metrics["cadence_moy"] + 5)
    
    # Recovery advice
    if metrics["score_recup"] < 50:
        metrics["conseil_recup"] = "Journée off ou footing très léger conseillé."
    elif metrics["score_recup"] < 70:
        metrics["conseil_recup"] = "Une sortie facile Z2 max 45min serait parfaite."
    else:
        metrics["conseil_recup"] = "Tu es bien récupéré, tu peux enchaîner."
    
    # Volume target
    metrics["volume_cible"] = round(metrics["km_semaine"] * 1.05, 1) if metrics["km_semaine"] > 0 else 25
    metrics["nb_seances_cible"] = max(3, metrics["nb_seances"])
    
    # Session suggestions
    if metrics["pct_z4_z5"] > 25:
        metrics["sortie_demain"] = "repos ou footing récup Z1 30min"
        metrics["sortie_conseillee"] = "footing récupération 40min Z2 tranquille"
    elif metrics["nb_seances"] < 2:
        metrics["sortie_demain"] = "footing endurance 45min Z2"
        metrics["sortie_conseillee"] = "sortie endurance 45-50min en Z2"
    else:
        metrics["sortie_demain"] = "footing modéré 50min avec 10min tempo"
        metrics["sortie_conseillee"] = "sortie progressive : 40min Z2 + 10min tempo"
    
    metrics["focus_seance"] = "maintenir une allure régulière"
    metrics["km_projetes"] = round(metrics["km_semaine"] + 8, 1)
    
    # Week sessions plan
    metrics["seance_mardi"] = "fractionné court (10x400m)" if metrics["pct_z4_z5"] < 20 else "footing récup"
    metrics["seance_jeudi"] = "tempo 30min" if metrics["pct_z4_z5"] < 25 else "footing Z2"
    metrics["seance_weekend"] = "sortie longue 1h30" if metrics["km_semaine"] > 25 else "sortie longue 1h"
    
    # Zone advice
    if metrics["pct_z1_z2"] < 60:
        metrics["conseil_zones"] = "Tu manques de volume en Z2, ralentis sur les sorties faciles."
        metrics["statut_zones"] = "un peu au-dessus de l'idéal"
    elif metrics["pct_z4_z5"] < 10:
        metrics["conseil_zones"] = "Tu peux ajouter un peu d'intensité, 1 séance tempo/semaine."
        metrics["statut_zones"] = "dans la cible"
    else:
        metrics["conseil_zones"] = "Bon équilibre, continue comme ça !"
        metrics["statut_zones"] = "dans la cible"
    
    # Goal comparison
    if "allure_cible" in metrics and "allure_moy" in metrics:
        try:
            current_parts = metrics["allure_moy"].split(":")
            target_parts = metrics["allure_cible"].split(":")
            current_secs = int(current_parts[0]) * 60 + int(current_parts[1])
            target_secs = int(target_parts[0]) * 60 + int(target_parts[1])
            diff = current_secs - target_secs
            
            if diff < -10:
                metrics["ecart_allure"] = "déjà au-dessus de ton objectif !"
                metrics["commentaire_ecart"] = "au-dessus de l'objectif"
            elif diff < 20:
                metrics["ecart_allure"] = "proche de l'objectif"
                metrics["commentaire_ecart"] = "très proche"
            else:
                metrics["ecart_allure"] = f"à {diff}s/km de l'objectif"
                metrics["commentaire_ecart"] = "en progression"
        except:
            metrics["ecart_allure"] = "en bonne progression"
            metrics["commentaire_ecart"] = "correct"
    
    # Estimated finish time
    if "jours_restants" in metrics and metrics["jours_restants"] > 0:
        metrics["temps_estime"] = "ton objectif temps"  # Simplified
    
    # Week appreciation
    if metrics["km_semaine"] < 15:
        metrics["appreciation_semaine"] = "légère"
        metrics["conseil_semaine"] = "augmente progressivement le volume"
        metrics["charge_semaine"] = "faible"
    elif metrics["km_semaine"] > 50:
        metrics["appreciation_semaine"] = "chargée"
        metrics["conseil_semaine"] = "récupère bien avant de relancer"
        metrics["charge_semaine"] = "élevée"
    else:
        metrics["appreciation_semaine"] = "équilibrée"
        metrics["conseil_semaine"] = "continue sur ce rythme"
        metrics["charge_semaine"] = "modérée"
    
    # Explanations for "pourquoi" questions
    metrics["explication"] = "L'entraînement fonctionne par cycles de stress et récupération. Le corps s'adapte pendant le repos."
    metrics["reponse_pourquoi"] = "C'est lié à la façon dont le corps s'adapte à l'effort."
    metrics["explication_detaillee"] = "Le principe de surcompensation : après un stress, le corps se renforce pour mieux supporter le prochain effort"
    metrics["conseil_pratique"] = "alterner séances dures et faciles, ne jamais enchaîner 2 séances intenses"
    
    # Injury placeholders
    metrics["type_douleur"] = "persistante ou qui augmente à l'effort"
    metrics["zone_corps"] = "tendons et articulations"
    
    return metrics


def generate_chat_response(
    message: str,
    workouts: List[dict],
    user_goal: dict = None
) -> str:
    """
    Generate a chat response based on the user's message.
    100% rule-based, no LLM involved.
    """
    
    # Detect category
    category = detect_category(message)
    
    # Calculate metrics
    base_metrics = calculate_training_metrics(workouts, user_goal)
    metrics = calculate_derived_metrics(base_metrics)
    
    # Get templates for category
    templates = TEMPLATES.get(category, TEMPLATES["fallback"])
    
    # Select random template
    template = random.choice(templates)
    
    # Fill in variables
    try:
        response = template.format(**metrics)
    except KeyError as e:
        # Fallback if template variable missing
        response = random.choice(TEMPLATES["fallback"])
    
    return response


# ============================================================
# PREMIUM & MESSAGE LIMIT HELPERS
# ============================================================

def check_message_limit(message_count: int, max_messages: int = 30) -> Tuple[bool, str]:
    """Check if user has reached monthly message limit"""
    if message_count >= max_messages:
        return False, "Limite mensuelle atteinte (30 msg). Passe à l'offre annuelle pour illimité ou attends le mois prochain !"
    return True, ""


def get_remaining_messages(message_count: int, max_messages: int = 30) -> int:
    """Get remaining messages for the month"""
    return max(0, max_messages - message_count)
