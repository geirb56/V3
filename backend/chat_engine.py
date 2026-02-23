"""
CardioCoach - Moteur de Chat 100% Python + RAG
Sans aucun LLM (ni local, ni cloud, ni WebLLM)
Déterministe, rapide (<1s), offline, naturel, ultra-humain
"""

import random
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

# Charger la base de connaissances
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")

def load_knowledge_base() -> Dict:
    """Charge la base de connaissances statique"""
    try:
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement knowledge_base: {e}")
        return {}

KNOWLEDGE_BASE = load_knowledge_base()

# ============================================================
# TEMPLATES PAR CATÉGORIE (10-15 variantes par bloc)
# ============================================================

TEMPLATES = {
    # ==================== CATÉGORIE 1: FATIGUE ====================
    "fatigue": {
        "keywords": ["fatigue", "fatigué", "épuisé", "crevé", "lourd", "lourdeur", "épuisement", "vidé", "mort", "claqué", "cramé", "hs", "naze", "lessivé", "ko"],
        "intros": [
            "T'as vraiment tout donné, respect ! 💪",
            "Super mental pour finir malgré la lourdeur !",
            "Bravo, t'as tenu jusqu'au bout 🔥",
            "T'as poussé fort, chapeau !",
            "Même fatigué t'as donné, c'est énorme !",
            "T'as géré comme un chef malgré tout 😅",
            "Respect pour l'effort malgré la lourdeur !",
            "T'as du mental d'acier !",
            "T'as assuré grave !",
            "T'es un guerrier, même quand c'est dur !",
            "Super combat, t'as pas lâché !",
            "Chapeau bas, t'as fini malgré tout !",
            "La fatigue t'a pas eu, bien joué !",
            "T'as montré du caractère aujourd'hui !",
            "Fier de toi pour avoir tenu !"
        ],
        "analyses": [
            "Ton allure a décroché de {decrochage}% sur la fin avec une FC qui monte → t'es clairement en fatigue accumulée. Ton ratio est à {ratio}, ça veut dire que tu as beaucoup chargé sans assez récupérer.",
            "Lourdeur en fin de séance → ta charge récente est haute ({charge}), ton corps te dit de ralentir un peu. C'est pas grave, c'est normal.",
            "Ratio {ratio} élevé → surcharge légère, rien d'alarmant mais faut calmer le jeu quelques jours.",
            "T'as une petite surcharge (ratio {ratio}) → c'est pas la fin du monde mais écoute ton corps.",
            "Tes jambes ont lâché sur la fin, c'est le signe d'une fatigue qui s'accumule. Normal après {nb_seances} séances cette semaine !",
            "La FC qui grimpe alors que l'allure baisse = signe classique de fatigue. Ton corps bosse dur pour compenser.",
            "Avec {km_semaine} km cette semaine, c'est logique de sentir un peu de lourdeur. Ton corps absorbe la charge.",
            "La fatigue que tu ressens c'est ton corps qui s'adapte. C'est un bon signe si tu récupères bien après !",
            "Ton décrochage d'allure sur la fin montre que t'as bien poussé. C'est positif, tu travailles tes limites.",
            "Quand les jambes sont lourdes dès le début, c'est souvent un manque de récup ou d'hydratation."
        ],
        "conseils": [
            "Demain footing très facile 40 min Z2 max ou jour off complet, hydrate-toi bien et dors tôt !",
            "Repose-toi, prends soin de tes jambes avec un peu d'étirements doux. Ça va recharger vite.",
            "Baisse l'intensité pendant 2-3 jours, ton corps te remerciera et tu reviendras plus fort.",
            "Priorise sommeil et récupération active cette semaine. C'est là que les vrais progrès se font !",
            "Prends un jour off complet si t'en ressens le besoin. Mieux vaut un jour de repos qu'une blessure.",
            "Hydrate-toi bien (2L minimum), mange des glucides et au lit tôt ce soir !",
            "Un petit massage ou du foam roller sur les jambes peut vraiment aider à récupérer.",
            "Si la fatigue persiste plus de 3 jours, prends une vraie semaine de décharge.",
            "Là t'as besoin de récup active : marche, vélo tranquille, natation... mais pas de course intense.",
            "Écoute ton corps : s'il dit stop, c'est qu'il a besoin de récupérer pour mieux repartir."
        ],
        "relances": [
            "C'était lourd dès le km 3 ou seulement sur la fin ?",
            "Tu as dormi combien d'heures ces derniers jours ?",
            "Hydratation au top cette semaine ou t'as un peu zappé ?",
            "Tu as senti tes jambes lourdes après combien de km ?",
            "T'as eu des courbatures avant cette séance ?",
            "C'est la première fois cette semaine que tu te sens comme ça ?",
            "Tu manges assez de glucides en ce moment ?",
            "T'as du stress au boulot ou perso qui pourrait jouer ?",
            "Tu fais des étirements ou du foam roller après tes séances ?",
            "T'as l'impression que c'est une fatigue musculaire ou plutôt générale ?",
            "Tu sens une différence entre tes deux jambes ?",
            "Ça fait combien de jours que tu t'entraînes sans break ?"
        ]
    },
    
    # ==================== CATÉGORIE 2: ALLURE/CADENCE ====================
    "allure_cadence": {
        "keywords": ["allure", "cadence", "pace", "vitesse", "rythme", "tempo", "foulée", "pas", "spm", "min/km", "lent", "rapide", "vite"],
        "intros": [
            "Alors, parlons technique ! 🎯",
            "Bonne question sur le rythme !",
            "Ton allure, c'est un sujet important 👟",
            "La cadence, c'est la clé d'une foulée efficace !",
            "Ah l'allure, le nerf de la guerre !",
            "Super question technique !",
            "T'as raison de t'intéresser à ça !",
            "La cadence, c'est souvent sous-estimé !",
            "Ton rythme actuel, décortiquons ça !",
            "Allure et cadence, les deux piliers de la perf !",
            "Bonne réflexion sur ta foulée !",
            "C'est malin de bosser là-dessus !"
        ],
        "analyses": [
            "Ta cadence moyenne est de {cadence} spm. {cadence_comment} L'idéal c'est entre 170 et 180, ça réduit l'impact sur les articulations.",
            "Ton allure moyenne de {allure}/km est {allure_comment}. Par rapport à ta zone cible, t'es {zone_comment}.",
            "Avec une cadence de {cadence}, {cadence_detail}. Une foulée plus rapide = moins de stress sur les genoux.",
            "Ton pace de {allure}/km montre que {allure_analysis}. C'est cohérent avec ton niveau actuel.",
            "La variabilité de ton allure est {variabilite}. {variabilite_comment}",
            "En regardant tes dernières sorties, ta cadence varie entre {cadence_min} et {cadence_max}. {cadence_conseil}",
            "Ton allure en endurance ({allure}) correspond bien à la zone {zone}. C'est {zone_feedback}.",
            "Avec {km_semaine} km à {allure}/km de moyenne, tu travailles bien ton endurance de base.",
            "Ta foulée actuelle ({cadence} spm) est {foulée_comment}. On peut optimiser ça !",
            "L'écart entre ton allure facile et ton allure tempo est de {ecart}. C'est {ecart_comment}."
        ],
        "conseils": [
            "Pour augmenter ta cadence, fais des gammes : montées de genoux, talons-fesses, 2x par semaine pendant 10 min.",
            "Essaie de courir au métronome à 175 bpm pendant quelques sorties, tu vas sentir la différence !",
            "Pour le pace, travaille des séances de seuil : 3x10 min à allure semi-marathon avec 3 min récup.",
            "Les côtes courtes (30-60 sec) sont géniales pour améliorer naturellement la cadence.",
            "Pour une meilleure foulée : pense à lever les genoux et à atterrir sous ton centre de gravité.",
            "Intègre des accélérations progressives (fartlek) dans tes sorties faciles pour varier les allures.",
            "Le travail de cadence se fait mieux en légère descente au début, c'est plus naturel.",
            "Pour l'allure spécifique, fais une séance par semaine de fractionné court (200-400m).",
            "Pense à relâcher les épaules et les bras, ça aide à fluidifier la foulée.",
            "Un bon exercice : 4x30 sec rapide / 30 sec lent pour travailler les changements d'allure."
        ],
        "relances": [
            "Tu fais déjà du travail de foulée ou des gammes ?",
            "T'as une montre qui te donne la cadence en direct ?",
            "Tu vises quoi comme allure sur ta prochaine course ?",
            "T'as déjà essayé le métronome pour la cadence ?",
            "Tu sens une différence de foulée en fin de séance ?",
            "T'as l'impression d'avoir une foulée plutôt longue ou courte ?",
            "Tu fais du fractionné régulièrement ?",
            "T'as des douleurs qui pourraient être liées à ta foulée ?",
            "Tu cours plutôt sur l'avant-pied, médio-pied ou talon ?",
            "Tes chaussures sont adaptées à ta foulée ?"
        ]
    },
    
    # ==================== CATÉGORIE 3: RÉCUPÉRATION ====================
    "recuperation": {
        "keywords": ["récup", "recuperation", "repos", "récupérer", "off", "pause", "break", "relâche", "décharge", "régénération"],
        "intros": [
            "La récup, c'est là que la magie opère ! ✨",
            "Ah la récupération, le secret des champions !",
            "Bonne question, la récup c'est crucial !",
            "T'as raison de penser récup !",
            "Le repos, c'est aussi de l'entraînement !",
            "Smart de s'intéresser à ça ! 🧠",
            "La récup, c'est 50% de la progression !",
            "Récupérer, c'est pas être fainéant, c'est être malin !",
            "Bien vu, beaucoup négligent cet aspect !",
            "La récup active, parlons-en !",
            "T'inquiète, je vais t'aider là-dessus !",
            "C'est THE sujet important !"
        ],
        "analyses": [
            "Avec {nb_seances} séances et {km_semaine} km cette semaine, ton corps a besoin de {recup_besoin}.",
            "Ton ratio charge/récup est de {ratio}. {ratio_comment} La zone verte c'est entre 0.8 et 1.2.",
            "Ta dernière semaine de décharge remonte à {derniere_decharge}. {decharge_comment}",
            "En regardant ta charge des 4 dernières semaines, {charge_evolution}. {charge_conseil}",
            "Tu as enchaîné {jours_consecutifs} jours sans repos. {consecutifs_comment}",
            "Ton volume actuel ({km_semaine} km) par rapport à ta moyenne ({km_moyenne} km) est {volume_comment}.",
            "La qualité de ta récup dépend de ton sommeil, ton hydratation et ton alimentation. {recup_analyse}",
            "Après une séance intense comme celle-ci, compte 48-72h pour une récup complète des muscles.",
            "Ton corps montre des signes de {signes_recup}. C'est {interpretation}.",
            "La récup active (marche, vélo léger) est plus efficace que le repos total dans ton cas."
        ],
        "conseils": [
            "Prévois au moins 1-2 jours de repos ou récup active par semaine, c'est non négociable.",
            "Une semaine de décharge (volume -30-40%) toutes les 3-4 semaines, c'est la base.",
            "Post-séance : étirements doux 10 min + 500ml d'eau + collation protéinée dans l'heure.",
            "Le foam roller 10-15 min sur les jambes, ça fait des miracles pour la récup.",
            "Dormir avant minuit = récup x2. Le sommeil avant minuit est plus réparateur.",
            "En récup active, vise 60-65% de ta FC max, pas plus. C'est du vrai repos actif.",
            "Les bains froids (10-15°C, 10-15 min) après une grosse séance réduisent l'inflammation.",
            "Hydrate-toi tout au long de la journée, pas seulement pendant et après l'effort.",
            "Les massages réguliers (1x/mois minimum) sont un investissement dans ta longévité.",
            "Écoute les signaux : jambes lourdes 2+ jours = besoin de plus de récup."
        ],
        "relances": [
            "Tu prends combien de jours off par semaine en général ?",
            "T'as une routine de récup post-séance ?",
            "Tu dors combien d'heures en moyenne ?",
            "Tu fais du foam roller ou des massages ?",
            "Tu t'hydrates bien tout au long de la journée ?",
            "Ça fait combien de temps ta dernière semaine tranquille ?",
            "Tu sens que t'as besoin de plus de repos en ce moment ?",
            "T'as des courbatures qui persistent plus de 48h ?",
            "Tu fais de la récup active genre vélo ou natation ?",
            "T'as essayé les bains froids ou la douche froide ?"
        ]
    },
    
    # ==================== CATÉGORIE 4: PLAN/PROCHAINE SORTIE ====================
    "plan": {
        "keywords": ["plan", "programme", "prochaine", "demain", "semaine", "planning", "organiser", "prévoir", "quoi faire", "entraînement"],
        "intros": [
            "Planifions ta semaine ! 📅",
            "Ok, voyons ce qu'on peut faire !",
            "Bonne idée de planifier à l'avance !",
            "Je te propose un plan adapté !",
            "Allez, on organise tout ça !",
            "C'est parti pour ta prochaine séance !",
            "Je regarde tes données et je te dis ! 🔍",
            "T'as bien fait de demander !",
            "On va optimiser ta semaine !",
            "Voilà ce que je te conseille !",
            "Avec ce que t'as fait, voici la suite !",
            "Je te fais un plan sur mesure !"
        ],
        "analyses": [
            "Cette semaine t'as fait {km_semaine} km sur {nb_seances} séances. {analyse_semaine}",
            "Ton ratio charge/récup est de {ratio}, donc {ratio_implication} pour la suite.",
            "En regardant tes zones cette semaine : {zones_resume}. {zones_conseil}",
            "Vu ta charge actuelle ({charge}), {charge_recommandation}.",
            "Ton corps a bien absorbé {km_semaine} km, {adaptation_comment}.",
            "La répartition intensité/endurance cette semaine est {repartition}. {repartition_comment}",
            "Ta progression sur le dernier mois montre {progression}. On peut {progression_action}."
        ],
        "conseils": [
            "Demain je te conseille : footing 45-50 min en Z2, tranquille, pour bien récupérer.",
            "Ta prochaine séance qualité : 6x1000m à allure 10km avec 2 min récup. Ça va te faire du bien !",
            "Cette semaine, vise : 1 sortie longue (1h15-1h30), 1 séance tempo, 2 footings faciles.",
            "Pour ta prochaine sortie : fartlek libre, 8-10 accélérations de 30 sec quand tu le sens.",
            "Je te suggère un jour de repos complet demain, puis reprise douce mardi.",
            "Prochaine séance idéale : côtes ! 8-10 répétitions de 45 sec, récup descente en trottinant.",
            "Planning semaine : Lundi off, Mardi footing 40min, Mercredi fractionné, Jeudi off, Vendredi footing, Samedi sortie longue.",
            "Pour varier : essaie une séance de fartlek nature, accélère quand t'as envie, récup quand tu veux.",
            "Ta prochaine sortie longue : 1h20-1h30 à allure confort, sans regarder la montre, juste au feeling.",
            "Je te propose du travail de seuil : 3x12 min à allure semi, 3 min récup entre chaque."
        ],
        "relances": [
            "T'as des contraintes particulières cette semaine ?",
            "Tu préfères courir le matin ou le soir ?",
            "T'as un objectif de course en vue ?",
            "Combien de séances tu peux caser cette semaine ?",
            "Tu veux bosser quoi en priorité : endurance ou vitesse ?",
            "T'as accès à une piste ou des côtes ?",
            "Tu cours seul ou en groupe ?",
            "T'as une durée max pour tes séances ?",
            "Tu veux que je te fasse un plan pour la semaine complète ?",
            "T'es plutôt du genre régulier ou ça dépend des semaines ?"
        ]
    },
    
    # ==================== CATÉGORIE 5: ANALYSE SEMAINE ====================
    "analyse_semaine": {
        "keywords": ["semaine", "bilan", "résumé", "analyse", "comment", "ça va", "forme", "état", "review", "point", "zones", "cardiaques", "cardiaque", "intensité", "endurance", "tempo"],
        "intros": [
            "Faisons le point sur ta semaine ! 📊",
            "Allez, je t'analyse tout ça !",
            "Voyons ce que tu as fait !",
            "Bilan de la semaine, c'est parti !",
            "Je regarde tes stats !",
            "Ok, décortiquons ta semaine !",
            "Ton point hebdo, le voilà !",
            "Analyse complète incoming !",
            "Je te fais le topo !",
            "Regardons ça ensemble !",
            "Ta semaine en résumé !",
            "C'est l'heure du bilan !"
        ],
        "analyses": [
            "Cette semaine : {km_semaine} km sur {nb_seances} séances, {duree_totale} de course. {appreciation}",
            "Côté zones : {z1z2}% en endurance, {z3}% en tempo, {z4z5}% en intensif. {zones_verdict}",
            "Ta charge est {charge_niveau} avec un ratio de {ratio}. {charge_interpretation}",
            "Par rapport à la semaine dernière : {comparaison_km} sur le volume, {comparaison_intensite} sur l'intensité.",
            "Ton allure moyenne ({allure}/km) est {allure_evolution} par rapport à d'habitude.",
            "Tu as couru {nb_jours} jours sur 7. {regularite_comment}",
            "La répartition de tes séances : {repartition_types}. {repartition_verdict}",
            "Tes sensations cette semaine semblent {sensations}. {sensations_conseil}",
            "Point fort : {point_fort}. Point à améliorer : {point_ameliorer}.",
            "En résumé : {resume_global}. {conseil_global}"
        ],
        "conseils": [
            "Pour la semaine prochaine, je te conseille de {conseil_semaine_prochaine}.",
            "Continue comme ça ! Maintiens ce volume et cette régularité.",
            "Pense à ajouter une séance de récup active pour mieux absorber la charge.",
            "La semaine prochaine, essaie d'ajouter un peu plus de travail en Z3-Z4.",
            "Bien joué ! Pour progresser encore, varie un peu plus les types de séances.",
            "Ta base d'endurance est solide. Tu peux commencer à ajouter du travail spécifique.",
            "Attention à ne pas augmenter trop vite. La règle des 10% max par semaine !",
            "Pour la suite, je te suggère une semaine de consolidation avant d'augmenter.",
            "T'es sur la bonne voie ! Reste régulier et les progrès viendront.",
            "Pense à intégrer une sortie longue par semaine si c'est pas déjà fait."
        ],
        "relances": [
            "Comment tu t'es senti globalement cette semaine ?",
            "T'as des douleurs ou gênes à signaler ?",
            "Le volume te semble gérable ou un peu trop ?",
            "T'as pu respecter toutes les séances prévues ?",
            "Tu veux qu'on ajuste le plan pour la semaine prochaine ?",
            "T'es satisfait de ta semaine ?",
            "Y a des séances que t'as trouvées trop dures ?",
            "Tu veux qu'on parle d'un aspect en particulier ?",
            "T'as bien récupéré entre les séances ?",
            "Des objectifs spécifiques pour la semaine prochaine ?"
        ]
    },
    
    # ==================== CATÉGORIE 6: MOTIVATION ====================
    "motivation": {
        "keywords": ["motivation", "motivé", "démotivé", "envie", "flemme", "dur", "difficile", "lassé", "ennui", "routine", "marre", "abandonner", "moral"],
        "intros": [
            "Hey, c'est normal d'avoir des coups de mou ! 💙",
            "La motivation, ça va et ça vient, t'inquiète !",
            "Je comprends, on passe tous par là !",
            "C'est humain de se sentir comme ça !",
            "Eh, même les pros ont des jours sans !",
            "T'es pas seul, ça arrive à tout le monde !",
            "La démotivation, c'est un signal, pas une faiblesse !",
            "On va trouver une solution ensemble !",
            "C'est ok de pas être à fond tout le temps !",
            "La course c'est un marathon, pas un sprint... littéralement ! 😄",
            "Ton honnêteté, c'est déjà un bon signe !",
            "On va relancer la machine !"
        ],
        "analyses": [
            "Quand la motivation baisse, c'est souvent signe de fatigue accumulée ou de routine trop monotone.",
            "Vu ton historique, t'as fait {km_total} km ces dernières semaines. {charge_impact_motivation}",
            "La lassitude peut venir d'objectifs trop lointains ou pas assez stimulants.",
            "Parfois le corps dit stop avant la tête. La démotivation peut être un signal de récup nécessaire.",
            "La routine tue la motivation. Si t'enchaînes les mêmes parcours, c'est normal de saturer.",
            "Le surentraînement a la démotivation comme symptôme classique. {surentrainement_check}",
            "Courir seul tout le temps peut peser sur le moral à la longue.",
            "L'hiver, la météo et la luminosité impactent naturellement la motivation.",
            "Si t'as pas d'objectif clair, c'est dur de rester motivé sur la durée.",
            "La comparaison avec les autres sur les réseaux peut aussi démotiver. Focus sur TON parcours !"
        ],
        "conseils": [
            "Change de parcours ! Découvre un nouveau coin, ça relance souvent la motivation.",
            "Fixe-toi un mini-objectif atteignable cette semaine : juste 3 sorties, peu importe la durée.",
            "Essaie de courir avec quelqu'un, même une fois. Ça change tout !",
            "Autorise-toi une vraie pause de 4-5 jours. Parfois c'est le meilleur remède.",
            "Inscris-toi à une petite course fun, ça donne un objectif concret.",
            "Écoute un nouveau podcast ou de la musique que t'adores pendant ta sortie.",
            "Oublie la montre pendant une sortie. Cours au feeling, pour le plaisir.",
            "Rappelle-toi pourquoi t'as commencé. C'était quoi ta motivation initiale ?",
            "Varie les activités : vélo, natation, rando... Le cross-training peut relancer l'envie.",
            "Récompense-toi après une bonne semaine. T'as le droit !"
        ],
        "relances": [
            "C'est depuis quand que tu te sens comme ça ?",
            "T'as un objectif de course en ce moment ?",
            "Tu cours toujours seul ou des fois en groupe ?",
            "T'as des parcours variés ou c'est toujours le même ?",
            "Y a un aspect de ta vie qui pourrait impacter ton moral ?",
            "T'as essayé de courir sans montre récemment ?",
            "C'est plus une flemme physique ou mentale ?",
            "Tu dors bien en ce moment ?",
            "T'as pris des vacances de course récemment ?",
            "Qu'est-ce qui te motivait au début ?"
        ]
    },
    
    # ==================== CATÉGORIE 7: MÉTÉO ====================
    "meteo": {
        "keywords": ["météo", "temps", "pluie", "vent", "chaud", "froid", "chaleur", "canicule", "orage", "neige", "verglas", "humidité"],
        "intros": [
            "Ah la météo, ça change tout ! 🌤️",
            "Bien vu de penser aux conditions !",
            "La météo, faut savoir s'adapter !",
            "Courir par tous les temps, c'est un art !",
            "Les conditions, c'est important à gérer !",
            "Bonne question, ça impacte vraiment la perf !",
            "S'adapter à la météo, c'est être un vrai coureur !",
            "La météo, on peut pas la changer, mais on peut s'y préparer !",
            "T'as raison de t'interroger là-dessus !",
            "Les conditions extérieures, parlons-en !"
        ],
        "analyses": [
            "Par temps chaud (+25°C), le corps dépense plus d'énergie pour se refroidir. Résultat : même effort = allure plus lente.",
            "Le vent de face peut te coûter 10-20 sec/km à effort équivalent. C'est pas toi qui es moins bon !",
            "Par temps froid (<5°C), les muscles mettent plus de temps à chauffer. L'échauffement est crucial.",
            "L'humidité élevée (>70%) rend l'évacuation de la chaleur plus difficile. Ton corps surchauffe plus vite.",
            "La pluie légère n'impacte pas vraiment la perf si t'es bien équipé. C'est même rafraîchissant !",
            "Par forte chaleur, ta FC sera naturellement plus haute pour la même allure. C'est physiologique.",
            "Le froid sec est plus facile à gérer que le froid humide. L'humidité traverse les couches.",
            "Les conditions difficiles renforcent le mental. C'est un investissement pour les courses !",
            "Courir par mauvais temps te prépare à toutes les situations le jour J.",
            "La météo impacte aussi ta récupération. Par forte chaleur, hydrate-toi encore plus après."
        ],
        "conseils": [
            "Par chaleur : ralentis de 15-30 sec/km, hydrate-toi toutes les 15-20 min, mouille ta casquette.",
            "Par temps froid : couche-toi bien (3 couches), protège tes extrémités, allonge l'échauffement à 15 min.",
            "Par vent fort : pars face au vent et rentre vent dans le dos. T'auras plus d'énergie pour finir !",
            "Sous la pluie : vêtements techniques qui sèchent vite, casquette, et prévois des chaussettes de rechange.",
            "Par forte chaleur : cours tôt le matin ou tard le soir, évite 12h-16h à tout prix.",
            "Par temps humide : choisis des vêtements respirants et évite le coton qui garde l'humidité.",
            "En hiver : un tour de cou ou un buff protège bien les voies respiratoires du froid.",
            "Par conditions difficiles : réduis tes objectifs de chrono et focus sur l'effort ressenti.",
            "Pense à checker la météo avant de choisir ton parcours (ombre/soleil, abrité/exposé).",
            "Adapte toujours ta tenue à la température ressentie, pas à la température affichée !"
        ],
        "relances": [
            "Tu cours plutôt matin ou soir en ce moment ?",
            "T'as des parcours plus abrités pour les jours de vent ?",
            "Tu t'hydrates suffisamment par temps chaud ?",
            "T'as une tenue adaptée à toutes les conditions ?",
            "Tu préfères reporter ou t'adapter aux conditions ?",
            "T'as déjà couru sous la pluie battante ?",
            "Le froid te gêne ou t'aimes bien ?",
            "T'as une routine d'échauffement par temps froid ?",
            "Tu cours avec une casquette par forte chaleur ?",
            "La météo impacte beaucoup ta motivation ?"
        ]
    },
    
    # ==================== CATÉGORIE 8: NUTRITION ====================
    "nutrition": {
        "keywords": ["nutrition", "manger", "alimentation", "glucides", "protéines", "hydratation", "boire", "eau", "gel", "boisson", "repas", "petit-déjeuner", "récup", "crampe"],
        "intros": [
            "La nutrition, c'est le carburant ! ⛽",
            "Bien manger = bien courir !",
            "L'alimentation, sujet crucial !",
            "Ton corps a besoin du bon fuel !",
            "La nutrition, souvent négligée mais essentielle !",
            "Ce que tu manges impacte direct ta perf !",
            "Bonne question, parlons bouffe ! 🍝",
            "L'hydratation et la nutrition, les bases !",
            "T'as raison de t'y intéresser !",
            "La diététique du coureur, c'est important !"
        ],
        "analyses": [
            "Le running consomme environ 1 kcal/kg/km. Sur {km_semaine} km, t'as besoin de compenser !",
            "Les glucides sont le carburant principal du coureur. Ils doivent représenter 50-60% de ton alimentation.",
            "L'hydratation impacte direct la performance. 2% de déshydratation = -10% de perf.",
            "Les protéines (1.2-1.6g/kg/jour) sont essentielles pour la récupération musculaire.",
            "Le timing est important : manger 2-3h avant l'effort, recharger dans les 30min après.",
            "Les crampes sont souvent liées à un manque de sodium ou de magnésium.",
            "Une alimentation variée couvre généralement tous les besoins sans compléments.",
            "Le café (caféine) peut améliorer la performance de 2-3% si pris 1-2h avant.",
            "L'alcool la veille impacte la qualité du sommeil et donc la récupération.",
            "Les fibres sont importantes mais à éviter juste avant une séance (inconfort digestif)."
        ],
        "conseils": [
            "Avant une sortie longue : repas riche en glucides 2-3h avant (pâtes, riz, pain).",
            "Pendant l'effort (+1h30) : 30-60g de glucides/heure (gels, boisson énergétique, fruits secs).",
            "Après l'effort : dans les 30 min, collation glucides + protéines (banane + yaourt, lait chocolaté).",
            "Hydrate-toi tout au long de la journée, pas seulement pendant et après l'effort.",
            "Par temps chaud, ajoute du sel dans ta boisson ou mange des aliments salés.",
            "Évite les aliments gras et les fibres dans les 3h précédant une séance intense.",
            "Le petit-déjeuner pré-course : pain, confiture, banane, café. Testé et approuvé !",
            "Les fruits secs (abricots, dattes) sont parfaits pendant les sorties longues.",
            "Ne teste jamais un nouvel aliment ou gel le jour d'une course. Toujours à l'entraînement !",
            "En récup, les protéines végétales (légumineuses) sont aussi efficaces que les animales."
        ],
        "relances": [
            "Tu manges quoi avant tes sorties en général ?",
            "Tu t'hydrates pendant tes séances ?",
            "T'as déjà eu des problèmes digestifs en courant ?",
            "Tu prends des gels ou barres sur les longues sorties ?",
            "Tu manges dans les 30 min après ta séance ?",
            "Tu as des crampes régulièrement ?",
            "Tu bois combien de litres par jour environ ?",
            "T'as un petit-déjeuner type avant une course ?",
            "Tu évites certains aliments avant de courir ?",
            "Tu prends des compléments alimentaires ?"
        ]
    },
    
    # ==================== CATÉGORIE 9: BLESSURES ====================
    "blessures": {
        "keywords": ["blessure", "douleur", "mal", "genou", "cheville", "tibia", "tendon", "hanche", "mollet", "pied", "dos", "périostite", "bandelette", "aponévrose", "contracture"],
        "intros": [
            "Aïe, parlons de cette douleur 🩹",
            "La douleur, faut pas la négliger !",
            "Ok, voyons ce qui se passe !",
            "Ton corps t'envoie un signal, écoutons-le !",
            "Les blessures, c'est sérieux, on va en parler !",
            "Attention à cette gêne !",
            "Je t'aide à y voir plus clair !",
            "La prévention, c'est la clé !",
            "Ton corps te parle, on l'écoute !",
            "Une douleur = un message, décodons-le !"
        ],
        "analyses": [
            "Une douleur qui persiste plus de 3 jours mérite un avis médical ou kiné.",
            "Les douleurs au genou viennent souvent d'un déséquilibre hanches/fessiers ou d'une foulée inadaptée.",
            "Les périostites tibiales sont souvent causées par une augmentation trop rapide du volume.",
            "La bandelette ilio-tibiale se manifeste par une douleur externe du genou, souvent en descente.",
            "Les tendinites d'Achille nécessitent du repos et des exercices excentriques.",
            "Les douleurs plantaires (aponévrose) sont fréquentes chez les coureurs à forte charge.",
            "Une douleur musculaire (courbature) ≠ une douleur articulaire ou tendineuse.",
            "L'augmentation du volume de plus de 10%/semaine est la cause #1 des blessures.",
            "Le manque de renforcement musculaire prédispose aux blessures.",
            "Des chaussures usées (>800km) augmentent significativement le risque de blessure."
        ],
        "conseils": [
            "Règle d'or : si ça fait mal en courant et que ça empire, ARRÊTE. Le repos vaut mieux qu'une blessure longue.",
            "RICE dans les 48h : Repos, Ice (glace), Compression, Élévation.",
            "Si douleur articulaire, consulte un kiné spécialisé running, pas juste ton médecin généraliste.",
            "Le renforcement des hanches et fessiers prévient 80% des blessures du coureur.",
            "Genou : travaille les squats, fentes, et pont fessier. Ça stabilise toute la chaîne.",
            "Périostite : repos 1-2 semaines, puis reprise très progressive. Pas de raccourci possible.",
            "Tendon d'Achille : exercices excentriques (descendre sur la pointe, lentement). 3x15/jour.",
            "Bandelette : foam roller sur l'extérieur de la cuisse + étirements IT band.",
            "Mollet : check tes chaussures, souvent lié à un drop trop bas ou une transition trop rapide.",
            "Prévention : 15 min de renfo 3x/semaine suffit à réduire drastiquement le risque."
        ],
        "relances": [
            "Ça fait combien de temps que tu as cette douleur ?",
            "C'est plutôt en courant, après, ou tout le temps ?",
            "T'as changé quelque chose récemment (chaussures, volume, terrain) ?",
            "La douleur est localisée précisément ou diffuse ?",
            "Ça s'améliore avec l'échauffement ou ça empire ?",
            "T'as déjà eu cette douleur avant ?",
            "T'as vu un kiné ou médecin du sport ?",
            "Tu fais du renforcement musculaire régulièrement ?",
            "Tes chaussures ont combien de km ?",
            "La douleur te réveille la nuit ?"
        ]
    },
    
    # ==================== CATÉGORIE 10: PROGRESSION/STAGNATION ====================
    "progression": {
        "keywords": ["progression", "progresser", "stagnation", "stagner", "plateau", "améliorer", "performance", "chrono", "temps", "record", "pr", "vo2max", "vma"],
        "intros": [
            "La progression, parlons-en ! 📈",
            "T'inquiète, on va débloquer ça !",
            "Les plateaux, c'est normal et temporaire !",
            "Progresser, c'est un marathon, pas un sprint !",
            "Ta progression m'intéresse !",
            "Voyons comment te faire évoluer !",
            "La perf, c'est un travail de fond !",
            "On va trouver des pistes d'amélioration !",
            "T'as le potentiel, faut juste ajuster !",
            "Chaque coureur peut progresser, toi y compris !"
        ],
        "analyses": [
            "La progression n'est jamais linéaire. Les plateaux de 2-4 semaines sont normaux et nécessaires.",
            "Vu tes données, ta VMA estimée est autour de {vma} km/h. {vma_comment}",
            "Tu stagnes peut-être parce que tu fais toujours le même type de séances. La variété stimule la progression.",
            "Une stagnation après plusieurs mois de progression = ton corps s'adapte. C'est bon signe !",
            "Pour progresser en endurance, il faut paradoxalement aller plus lentement sur les sorties faciles.",
            "Ta cadence de {cadence} et ton allure de {allure} montrent {analyse_technique}.",
            "Les gains de VMA/VO2max prennent 6-12 mois de travail régulier. Patience !",
            "Un plateau peut aussi être signe de fatigue accumulée. As-tu assez récupéré ?",
            "Progresser = stress + récup. Si tu stresses toujours sans récupérer, tu plafonnes.",
            "Ta progression sur {periode} montre {evolution}. {evolution_comment}"
        ],
        "conseils": [
            "Pour casser un plateau : ajoute une séance de VMA par semaine (8x400m ou 6x500m).",
            "Varie les stimuli : côtes, fartlek, tempo, intervalles. Ton corps a besoin de nouveauté.",
            "Parfois, 1-2 semaines de décharge suffisent à relancer la progression.",
            "Travaille ta vitesse pure de temps en temps : 6-8 sprints de 20 sec, récup 2 min.",
            "L'endurance fondamentale (Z2) doit représenter 80% de ton volume. C'est la base de tout.",
            "Le travail de seuil (allure semi-marathon) améliore l'économie de course.",
            "Si tu stagnes en vitesse, bosse la cadence et la technique de foulée.",
            "Un coach ou un regard extérieur peut identifier des axes de progression invisibles pour toi.",
            "Analyse tes courses passées : où perds-tu du temps ? C'est là qu'il faut travailler.",
            "La force (renforcement) peut débloquer une stagnation chez beaucoup de coureurs."
        ],
        "relances": [
            "Tu stagnes depuis combien de temps environ ?",
            "C'est sur quel aspect : vitesse, endurance, les deux ?",
            "Tu fais du fractionné régulièrement ?",
            "T'as un objectif chrono précis ?",
            "Tu varies tes types de séances ?",
            "T'as pris des vacances de course récemment ?",
            "Tu travailles la technique de foulée ?",
            "Tu fais du renforcement musculaire ?",
            "T'as analysé tes courses récentes en détail ?",
            "Tu cours toujours sur le même terrain (route, trail, piste) ?"
        ]
    },
    
    # ==================== CATÉGORIE 11: PRÉPA COURSE ====================
    "prepa_course": {
        "keywords": ["course", "compétition", "10km", "semi", "marathon", "trail", "prépa", "objectif", "dossard", "inscription", "jour j"],
        "intros": [
            "Une course en vue, génial ! 🏃‍♂️",
            "La prépa course, c'est excitant !",
            "Ton objectif approche !",
            "On va te préparer au top !",
            "C'est parti pour la prépa !",
            "Ton dossard t'attend !",
            "La course, c'est LA motivation !",
            "On va tout planifier !",
            "Allez, objectif en ligne de mire !",
            "Ta course mérite une vraie prépa !"
        ],
        "analyses": [
            "Pour un 10km, compte 8-10 semaines de prépa. Pour un semi, 10-12. Pour un marathon, 12-16.",
            "À {jours_course} jours de ta course, tu es dans la phase {phase_prepa}. {phase_conseil}",
            "Vu ton allure actuelle ({allure}/km), ton potentiel sur {distance} est autour de {temps_estime}.",
            "Ta charge actuelle ({km_semaine} km/sem) est {charge_comment} pour préparer un {distance}.",
            "La dernière sortie longue doit avoir lieu 2-3 semaines avant la course, pas moins.",
            "La semaine avant la course : -50% de volume, maintien d'une petite intensité.",
            "Ton travail spécifique à l'allure cible doit représenter 10-15% du volume total.",
            "Tes zones cardiaques montrent {zones_analyse}. {zones_recommandation}",
            "Le jour J, pars sur une allure 5-10 sec plus lente que ton objectif les 5 premiers km.",
            "La gestion de course (pacing) est aussi importante que la forme physique."
        ],
        "conseils": [
            "Dernière semaine : réduis le volume de 50%, garde 2-3 courtes accélérations pour rester vif.",
            "Teste TOUT à l'entraînement : chaussures, tenue, nutrition, gel. Rien de nouveau le jour J !",
            "Repère le parcours si possible, ou étudie-le sur Google Maps. Savoir où sont les côtes aide.",
            "Prépare tes affaires la veille, avec une checklist. Moins de stress le jour J.",
            "Dors bien 2 nuits avant (la veille, le stress peut gêner le sommeil, c'est normal).",
            "Arrive tôt le jour J : parking, retrait dossard, échauffement, WC... ça prend du temps.",
            "Échauffement pré-course : 10-15 min de trot + quelques accélérations progressives.",
            "Stratégie de course : pars prudemment, accélère progressivement, finis fort si possible.",
            "Visualise ta course la veille : le départ, le parcours, tes sensations, l'arrivée.",
            "Post-course : marche, étire-toi, mange et bois dans l'heure. La récup commence tout de suite !"
        ],
        "relances": [
            "C'est quoi ta prochaine course ?",
            "Elle est dans combien de temps ?",
            "T'as un objectif de temps ?",
            "C'est ta première course sur cette distance ?",
            "T'as déjà fait un plan de prépa ?",
            "Tu connais le parcours ?",
            "T'as prévu ta stratégie de nutrition pendant la course ?",
            "T'as une tenue prévue ?",
            "Tu cours seul ou avec un groupe/pacer ?",
            "T'es plutôt stressé ou serein avant les courses ?"
        ]
    },
    
    # ==================== CATÉGORIE 12: MENTAL/STRESS ====================
    "mental": {
        "keywords": ["mental", "stress", "anxiété", "pression", "peur", "confiance", "doute", "nerveux", "angoisse", "trac"],
        "intros": [
            "Le mental, c'est 50% de la course ! 🧠",
            "Le stress, ça se gère !",
            "T'es pas seul à ressentir ça !",
            "Le mental se travaille comme le physique !",
            "Normal d'avoir le trac !",
            "La pression, on va l'apprivoiser !",
            "Ton mental est ta force cachée !",
            "Le doute, ça arrive à tout le monde !",
            "On va bosser cet aspect ensemble !",
            "La confiance, ça se construit !"
        ],
        "analyses": [
            "Le stress pré-course est normal et même utile : il prépare ton corps à la performance.",
            "Le doute est normal, même les champions en ont. La différence : ils courent quand même.",
            "Un stress chronique impacte la récupération et la progression. Il faut le prendre en compte.",
            "La visualisation positive active les mêmes zones cérébrales que l'action réelle. C'est puissant !",
            "Le 'mur' en course est souvent plus mental que physique. Ton corps peut bien plus que tu crois.",
            "Les pensées négatives arrivent, c'est normal. L'important c'est de ne pas les nourrir.",
            "La confiance vient de la préparation. Si t'es bien préparé, tu peux avoir confiance.",
            "Le stress de performance peut améliorer tes résultats (bon stress) ou les plomber (mauvais stress).",
            "Les routines pré-course réduisent l'anxiété : toujours le même échauffement, la même tenue...",
            "Le sommeil perturbé avant une course est très courant. C'est la nuit d'avant-avant qui compte."
        ],
        "conseils": [
            "Respiration carrée avant le départ : inspire 4s, bloque 4s, expire 4s, bloque 4s. Répète 5x.",
            "Visualise ta course en détail la veille : départ, parcours, sensations, arrivée triomphante.",
            "Découpe la course en segments : 'juste jusqu'au prochain ravito', 'juste 2 km de plus'...",
            "Prépare 2-3 mantras personnels pour les moments durs : 'Je suis fort', 'Un pas après l'autre'...",
            "Focus sur ce que tu contrôles (ta prépa, ta course) pas sur ce que tu ne contrôles pas (les autres, la météo).",
            "Si le doute arrive, rappelle-toi tes entraînements. Tu as fait le boulot.",
            "Le jour J, évite les gens négatifs ou stressés. Entoure-toi de bonnes ondes.",
            "Accepte que la course ne sera peut-être pas parfaite. Aucune course ne l'est.",
            "Célèbre le fait d'être à la ligne de départ. Beaucoup de gens n'osent même pas s'inscrire.",
            "Si tu paniques, reviens à ta respiration. C'est la base du contrôle mental."
        ],
        "relances": [
            "C'est quoi qui te stresse le plus ?",
            "T'as déjà essayé la visualisation ?",
            "Tu dors bien avant les courses ?",
            "T'as des mantras ou phrases qui t'aident ?",
            "Le stress c'est plutôt avant ou pendant la course ?",
            "T'as des routines pré-course ?",
            "C'est le chrono qui te met la pression ou autre chose ?",
            "T'as déjà eu un 'mur' mental en course ?",
            "Tu médites ou fais de la relaxation ?",
            "T'arrives à relativiser ou c'est difficile ?"
        ]
    },
    
    # ==================== CATÉGORIE 13: SOMMEIL ====================
    "sommeil": {
        "keywords": ["sommeil", "dormir", "dodo", "nuit", "insomnie", "fatigue", "sieste", "repos", "réveil", "coucher"],
        "intros": [
            "Le sommeil, c'est le meilleur dopant légal ! 😴",
            "Bien dormir = bien courir !",
            "La récup nocturne, sujet crucial !",
            "Le sommeil, souvent négligé mais essentiel !",
            "T'as raison de t'y intéresser !",
            "Le repos, c'est aussi de l'entraînement !",
            "Ton sommeil impacte direct ta perf !",
            "La nuit, c'est là que ton corps se répare !",
            "Parlons dodo !",
            "Le sommeil, l'arme secrète des champions !"
        ],
        "analyses": [
            "Le sommeil profond est la phase où tes muscles se réparent et où l'hormone de croissance est sécrétée.",
            "Un manque de sommeil chronique augmente le risque de blessure de 60%.",
            "7-9h de sommeil sont recommandées pour un coureur régulier. En période de charge : plutôt 8-9h.",
            "Le sommeil avant minuit est plus réparateur : les premiers cycles sont plus profonds.",
            "La qualité compte autant que la quantité. 7h de bon sommeil > 9h de sommeil haché.",
            "Le stress et les écrans bleus perturbent la production de mélatonine (hormone du sommeil).",
            "Après une séance intense, le corps a besoin de plus de sommeil pour récupérer.",
            "Le café après 14h peut impacter ton sommeil même si tu ne le ressens pas.",
            "La température idéale de la chambre pour dormir : 18-19°C.",
            "Une dette de sommeil se cumule et impacte la performance sur plusieurs jours."
        ],
        "conseils": [
            "Routine du soir : écrans off 1h avant, douche tiède, lecture, coucher à heure fixe.",
            "Si tu dors mal, une sieste de 20 min (pas plus) peut compenser sans perturber la nuit.",
            "Évite les repas trop copieux le soir, la digestion perturbe le sommeil.",
            "Le magnésium peut aider si tu as du mal à t'endormir ou des crampes nocturnes.",
            "Chambre fraîche, obscure et silencieuse = conditions optimales.",
            "Si le stress empêche de dormir : journal de gratitude ou liste de tâches pour 'vider' la tête.",
            "La veille de course, c'est la nuit d'avant-avant qui compte. Ne stresse pas si tu dors mal J-1.",
            "Un réveil à heure fixe (même le week-end) régule mieux le sommeil qu'une heure de coucher fixe.",
            "Évite l'alcool le soir : il endort mais perturbe la qualité du sommeil profond.",
            "En période de grosse charge, priorise le sommeil sur tout le reste. C'est là que tu progresses."
        ],
        "relances": [
            "Tu dors combien d'heures en moyenne ?",
            "Tu t'endors facilement ou ça prend du temps ?",
            "Tu te réveilles frais ou fatigué ?",
            "T'as une routine avant de dormir ?",
            "Tu regardes les écrans tard le soir ?",
            "Tu te réveilles souvent la nuit ?",
            "Tu fais des siestes ?",
            "Tu dors mieux ou moins bien après les grosses séances ?",
            "Le stress impacte ton sommeil ?",
            "T'as essayé des techniques de relaxation ?"
        ]
    },
    
    # ==================== CATÉGORIE 14: RENFORCEMENT ====================
    "renforcement": {
        "keywords": ["renfo", "renforcement", "musculation", "muscle", "gainage", "squat", "pompe", "abdos", "fessiers", "force", "gym"],
        "intros": [
            "Le renfo, l'arme anti-blessure ! 💪",
            "La musculation du coureur, sujet important !",
            "Bien vu de penser au renforcement !",
            "Le renfo, c'est pas que pour les bodybuilders !",
            "La force au service de la course !",
            "Le gainage, la base de tout !",
            "T'as raison, le renfo c'est crucial !",
            "Un coureur solide est un coureur efficace !",
            "Le renforcement, parlons-en !",
            "La prévention par le renfo !"
        ],
        "analyses": [
            "Le gainage renforce ton tronc et stabilise ta foulée. Moins d'énergie perdue = plus d'efficacité.",
            "Les fessiers sont les muscles les plus puissants de la foulée. Les négliger = blessures garanties.",
            "80% des blessures du coureur pourraient être évitées par un renfo régulier.",
            "Pas besoin de salle : les exercices au poids du corps suffisent largement.",
            "Le renfo améliore l'économie de course : tu dépenses moins d'énergie pour la même vitesse.",
            "2-3 séances de 15-20 min par semaine suffisent pour voir des résultats.",
            "Les squats et fentes travaillent toute la chaîne de propulsion : quads, fessiers, mollets.",
            "Le pont fessier isole bien les fessiers sans stresser les genoux.",
            "Les mollets sont souvent négligés mais essentiels pour l'amorti et la propulsion.",
            "Le renfo ne te fera pas prendre de masse si tu restes dans les hautes répétitions."
        ],
        "conseils": [
            "Routine de base : 3x30s de gainage (planche face + côtés), 3x12 squats, 3x10 fentes chaque jambe.",
            "Le pont fessier : allongé sur le dos, pieds au sol, monte le bassin. 3x15 reps.",
            "Pour les mollets : montées sur pointes (bilatéral puis unilatéral). 3x15 reps.",
            "Le Superman renforce le bas du dos : allongé à plat ventre, lève bras et jambes. 3x10.",
            "Fais ton renfo après une séance facile, pas avant une séance intense.",
            "La corde à sauter est top pour les mollets et la proprioception. 3x1 min.",
            "Le step-up sur marche travaille l'équilibre et la force unilaterale. 3x10 chaque jambe.",
            "Le clam shell (coquillage) renforce les abducteurs de hanche. 3x15 chaque côté.",
            "Pas motivé pour le renfo ? Fais-le devant une série Netflix, ça passe mieux !",
            "Intègre du renfo à ta routine : même 10 min 3x par semaine font la différence."
        ],
        "relances": [
            "Tu fais du renfo actuellement ?",
            "T'as du matériel ou tu bosses au poids du corps ?",
            "Tu préfères les exercices debout ou au sol ?",
            "T'as des zones à renforcer en priorité ?",
            "Tu fais du renfo avant ou après tes sorties ?",
            "T'as des douleurs qui pourraient être liées à un manque de renfo ?",
            "Tu connais les exercices de base pour coureurs ?",
            "Tu arrives à être régulier sur le renfo ?",
            "T'as déjà suivi un programme de renfo spécifique ?",
            "Le gainage, t'en fais ?"
        ]
    },
    
    # ==================== CATÉGORIE 15: ÉQUIPEMENT ====================
    "equipement": {
        "keywords": ["équipement", "chaussure", "basket", "montre", "gps", "tenue", "vêtement", "chaussette", "sac", "ceinture", "lampe", "frontale"],
        "intros": [
            "L'équipement, c'est important ! 👟",
            "Parlons matos !",
            "Bien équipé = bien préparé !",
            "Les chaussures, sujet crucial !",
            "Le bon équipement fait la différence !",
            "T'as raison de t'y intéresser !",
            "L'équipement, un investissement malin !",
            "Ton matos, parlons-en !",
            "Bien s'équiper, c'est la base !",
            "Les bons outils pour bien courir !"
        ],
        "analyses": [
            "Des chaussures usées (>600-800 km) perdent leur amorti et augmentent le risque de blessure.",
            "Le type de chaussure doit correspondre à ta foulée (pronatrice, neutre, supinatrice) et ton terrain.",
            "Une montre GPS n'est pas indispensable mais aide énormément à suivre sa progression.",
            "Les vêtements techniques évacuent la transpiration, contrairement au coton qui la retient.",
            "Le drop (différence talon/avant-pied) impacte la foulée. Une transition trop rapide vers low-drop = blessure.",
            "Les chaussettes de running réduisent les frottements et les ampoules.",
            "Une ceinture porte-bidon est utile pour les sorties de plus d'1h, surtout par temps chaud.",
            "La lampe frontale est indispensable pour courir le matin tôt ou le soir en hiver.",
            "Les lunettes de soleil réduisent la fatigue visuelle et protègent des UV.",
            "Le test en magasin spécialisé est le meilleur moyen de trouver LA bonne chaussure."
        ],
        "conseils": [
            "Change tes chaussures tous les 600-800 km, ou dès que tu sens moins d'amorti.",
            "Va dans un magasin spécialisé running pour un test de foulée et des conseils personnalisés.",
            "Aie 2 paires de chaussures en rotation : ça prolonge leur durée de vie et varie les stimuli.",
            "Teste tes chaussures de course à l'entraînement, jamais le jour J !",
            "Pour le trail, choisis des chaussures avec du grip et de la protection.",
            "Les vêtements sans coutures réduisent les frottements sur les longues distances.",
            "Une montre basique avec GPS suffit amplement pour débuter. Pas besoin du dernier modèle.",
            "Investis dans de bonnes chaussettes : c'est souvent négligé mais ça change tout.",
            "Par temps froid, privilégie les couches fines superposables plutôt qu'une grosse doudoune.",
            "Le sac d'hydratation type gilet est plus confortable que la ceinture pour le trail."
        ],
        "relances": [
            "Tes chaussures ont combien de km ?",
            "Tu connais ton type de foulée ?",
            "T'as été conseillé en magasin spécialisé ?",
            "Tu cours sur quel terrain principalement ?",
            "T'as une montre GPS ?",
            "Tu as des problèmes d'ampoules ?",
            "Tes chaussures sont confortables dès le début ou ça frotte ?",
            "Tu alternes plusieurs paires ?",
            "T'as le bon équipement pour toutes les conditions météo ?",
            "Tu portes des vêtements techniques ou du coton ?"
        ]
    },
    
    # ==================== CATÉGORIE 16: CHALEUR ====================
    "chaleur": {
        "keywords": ["chaleur", "chaud", "canicule", "été", "soleil", "surchauffe", "coup de chaud", "déshydratation", "transpiration"],
        "intros": [
            "Courir par chaleur, ça se gère ! ☀️",
            "La chaleur, faut s'adapter !",
            "Bonne question sur la gestion de la chaleur !",
            "L'été, c'est un défi pour les coureurs !",
            "La chaleur demande des ajustements !",
            "T'as raison, c'est un sujet important !",
            "Courir au frais, c'est mieux mais pas toujours possible !",
            "La chaleur, on peut l'apprivoiser !",
            "Gérer la chaleur, c'est essentiel !",
            "L'acclimatation à la chaleur, parlons-en !"
        ],
        "analyses": [
            "Par forte chaleur (+30°C), ton corps dépense beaucoup d'énergie pour se refroidir. Résultat : -15 à 30 sec/km à effort équivalent.",
            "L'humidité aggrave l'effet de la chaleur : la sueur ne s'évapore plus, le corps surchauffe.",
            "Les signes d'alerte coup de chaud : nausée, vertiges, confusion, arrêt de transpiration. STOP immédiat !",
            "L'acclimatation à la chaleur prend 10-14 jours. Après, le corps s'adapte mieux.",
            "La déshydratation de 2% réduit la performance de 10-20%. Et tu perds 1-2L/h par forte chaleur.",
            "Ta FC sera naturellement 10-15 bpm plus haute par temps chaud pour la même allure.",
            "Le corps ne peut pas se refroidir efficacement au-delà de 35°C avec forte humidité.",
            "Courir à la chaleur est un stress supplémentaire. Ta charge perçue est plus haute.",
            "L'hydratation doit commencer AVANT l'effort, pas pendant. Arrive déjà bien hydraté.",
            "Les vêtements clairs réfléchissent la chaleur, les sombres l'absorbent."
        ],
        "conseils": [
            "Par forte chaleur, ralentis de 15-30 sec/km et oublie le chrono. L'effort compte, pas l'allure.",
            "Cours tôt le matin (6h-8h) ou tard le soir (après 20h). Évite 12h-16h à tout prix.",
            "Hydrate-toi AVANT : 500ml dans les 2h précédant l'effort.",
            "Pendant l'effort : 150-250ml toutes les 15-20 min, avec des sels si +1h.",
            "Mouille ta casquette, ta nuque, tes avant-bras aux points d'eau. Le refroidissement externe aide.",
            "Choisis des parcours ombragés et proches de fontaines ou points d'eau.",
            "Vêtements clairs, légers, respirants, amples. Pas de coton !",
            "Si tu te sens mal (nausée, vertiges) : ARRÊTE, mets-toi à l'ombre, bois, et appelle à l'aide si besoin.",
            "Après la sortie : continue à boire, mange des aliments riches en eau (pastèque, concombre...).",
            "Pour t'acclimater : 10-14 jours de sorties modérées à la chaleur, en augmentant progressivement."
        ],
        "relances": [
            "Tu cours plutôt matin ou soir en été ?",
            "T'as des parcours ombragés ?",
            "Tu bois assez avant de partir ?",
            "T'emportes de l'eau avec toi ?",
            "T'as déjà eu des coups de chaud ?",
            "Tu mets une casquette ?",
            "Tes vêtements sont adaptés à la chaleur ?",
            "Tu sais reconnaître les signes de surchauffe ?",
            "Tu adaptes ton allure quand il fait chaud ?",
            "Tu arrives à courir régulièrement en été ?"
        ]
    },
    
    # ==================== CATÉGORIE 17: POST-COURSE ====================
    "post_course": {
        "keywords": ["après", "post", "marathon", "récup", "courbature", "récupération", "course terminée", "finisher"],
        "intros": [
            "Bravo pour ta course, finisher ! 🏅",
            "La récup post-course, c'est crucial !",
            "Bien joué d'avoir terminé !",
            "Après l'effort, le réconfort... et la récup !",
            "Ta course est faite, maintenant récupère !",
            "Félicitations, parlons récupération !",
            "Post-course, c'est le moment de prendre soin de toi !",
            "Ton corps a besoin de récupérer maintenant !",
            "La récup fait partie de la perf !",
            "Bien récupérer = mieux repartir !"
        ],
        "analyses": [
            "Après un marathon, compte 2-3 semaines de récup complète. Ton corps a subi un stress énorme.",
            "Les courbatures post-course (DOMS) sont normales et peuvent durer 3-5 jours.",
            "La fatigue post-course est multifactorielle : musculaire, tendineuse, immunitaire, mentale.",
            "Le glycogène musculaire met 24-48h à se reconstituer complètement. Mange des glucides !",
            "L'inflammation post-effort est normale et fait partie du processus de récupération.",
            "Le risque de blessure est élevé dans les 2 semaines post-course si tu reprends trop vite.",
            "La récup active (marche, vélo très léger) est plus efficace que le repos total.",
            "Ton système immunitaire est affaibli 24-72h après une course longue. Attention aux infections.",
            "Les douleurs qui persistent plus de 7 jours méritent un avis médical.",
            "La récup mentale compte aussi : savoure ta performance, même si elle n'était pas parfaite."
        ],
        "conseils": [
            "J+0 : Marche 10-15 min, étirements doux, mange et bois dans l'heure. Bain froid si possible.",
            "J+1 à J+3 : Repos ou marche/vélo très léger. Pas de course. Continue à bien manger et dormir.",
            "J+4 à J+7 : Footing très facile 20-30 min si les sensations sont bonnes. Sinon, encore repos.",
            "J+7 à J+14 : Reprise progressive, footings courts, pas d'intensité. Écoute ton corps.",
            "Après J+14 : Si tout va bien, tu peux reprendre un entraînement normal progressivement.",
            "Bois beaucoup les jours suivants : l'hydratation aide à évacuer les déchets métaboliques.",
            "Le foam roller ou massage aide à accélérer la récup musculaire.",
            "Mange des protéines pour la reconstruction musculaire, des glucides pour l'énergie.",
            "Dors plus que d'habitude : c'est pendant le sommeil que la récup se fait.",
            "Savoure ta performance ! Prends le temps de célébrer avant de penser à la prochaine."
        ],
        "relances": [
            "C'était quoi comme distance ta course ?",
            "Comment tu te sens physiquement ?",
            "T'as des courbatures où ?",
            "Tu as bien mangé et bu après ?",
            "C'est ta première course de cette distance ?",
            "T'as prévu combien de temps de récup ?",
            "Tu as des douleurs particulières ?",
            "Comment était ta course ? Content du résultat ?",
            "Tu as déjà un prochain objectif en tête ?",
            "Tu arrives à te reposer ou t'as envie de recourir ?"
        ]
    },
    
    # ==================== CATÉGORIE 18: QUESTIONS GÉNÉRALES ====================
    "general": {
        "keywords": ["conseil", "aide", "quoi", "comment", "pourquoi", "question", "avis", "pense", "sais pas"],
        "intros": [
            "Je suis là pour t'aider ! 🙌",
            "Bonne question !",
            "Je t'explique !",
            "Voyons ça ensemble !",
            "C'est parti !",
            "Je te dis ce que j'en pense !",
            "Allez, on regarde ça !",
            "Je suis ton coach, pose tes questions !",
            "T'as bien fait de demander !",
            "On va voir ça !"
        ],
        "analyses": [
            "En regardant tes données récentes, je vois que {observation_generale}.",
            "Ta régularité ({nb_seances} séances/semaine) est {regularite_comment}.",
            "Ton volume actuel ({km_semaine} km) est {volume_comment} pour ton niveau.",
            "La répartition de tes zones montre {zones_comment}.",
            "Ta progression ces dernières semaines est {progression_comment}.",
            "Ton ratio charge/récup ({ratio}) indique {ratio_comment}.",
            "Globalement, tu es sur une bonne dynamique. {dynamique_detail}",
            "J'ai noté que {pattern_observe}. C'est {pattern_interpretation}.",
            "En comparant avec tes objectifs, tu es {objectif_position}.",
            "Ce que je retiens de ton historique : {resume_historique}."
        ],
        "conseils": [
            "Mon conseil principal pour toi en ce moment : {conseil_principal}.",
            "Continue comme ça, t'es sur la bonne voie !",
            "Focus sur la régularité, c'est la clé de la progression.",
            "N'hésite pas à me poser des questions plus précises si tu veux approfondir.",
            "Je te conseille de {recommandation_specifique}.",
            "Pour progresser, {piste_progression}.",
            "Un point à améliorer : {point_amelioration}.",
            "Ta priorité devrait être : {priorite}.",
            "Si je devais te donner un seul conseil : {conseil_unique}.",
            "Reste à l'écoute de ton corps, c'est ton meilleur coach !"
        ],
        "relances": [
            "Tu veux qu'on parle d'un sujet en particulier ?",
            "T'as d'autres questions ?",
            "Y a un aspect de ton entraînement que tu veux creuser ?",
            "Comment je peux t'aider davantage ?",
            "Tu veux qu'on regarde un point précis ?",
            "T'as des objectifs spécifiques en ce moment ?",
            "Y a quelque chose qui te tracasse ?",
            "Tu veux un plan pour la semaine ?",
            "Des douleurs ou gênes à signaler ?",
            "Comment tu te sens globalement ?"
        ]
    },
    
    # ==================== CATÉGORIE 19: ROUTINE ====================
    "routine": {
        "keywords": ["routine", "habitude", "régularité", "discipline", "régulier", "tenir", "maintenir", "constance"],
        "intros": [
            "La routine, c'est la clé ! 🔑",
            "La régularité bat l'intensité !",
            "Créer une habitude, sujet important !",
            "La constance, c'est le secret !",
            "Bien vu de penser à ça !",
            "La routine, c'est ton meilleur allié !",
            "Installer une habitude, parlons-en !",
            "La discipline, ça se construit !",
            "La régularité, c'est 80% du succès !",
            "Les habitudes font les champions !"
        ],
        "analyses": [
            "Une habitude met environ 21-66 jours à s'installer. Patience !",
            "Vu ton historique, tu cours en moyenne {frequence} fois par semaine. {frequence_comment}",
            "La régularité est plus importante que l'intensité pour progresser sur le long terme.",
            "Les coureurs les plus constants sont ceux qui progressent le plus, pas les plus intenses.",
            "Courir le matin est souvent plus facile à tenir : moins d'imprévus, c'est fait !",
            "La routine crée un automatisme. Après quelques semaines, tu n'auras plus à te forcer.",
            "Les jours où t'as pas envie, une sortie courte vaut mieux que pas de sortie.",
            "La motivation est fluctuante, la discipline est constante. Construis sur la discipline.",
            "Ton cerveau résiste au changement les premières semaines. C'est normal, persévère !",
            "Une routine flexible (3-4 créneaux possibles/semaine) est plus tenable qu'une rigide."
        ],
        "conseils": [
            "Planifie tes séances comme des rendez-vous importants dans ton agenda.",
            "Prépare tes affaires la veille. Moins d'obstacles = plus de chances d'y aller.",
            "Trouve un partenaire d'entraînement, ça engage et motive.",
            "Commence petit : 2-3 sorties par semaine, puis augmente progressivement.",
            "Le matin, c'est souvent le meilleur créneau pour installer une routine.",
            "Associe ta séance à un trigger : 'Je cours après le café' ou 'Je cours avant la douche'.",
            "Autorise-toi à faire une sortie courte les jours difficiles. 15 min > 0 min.",
            "Récompense-toi après une bonne semaine de régularité.",
            "Ne cherche pas la motivation, cherche la discipline. La motivation suivra.",
            "Si tu rates une séance, ne culpabilise pas. Reprends simplement au prochain créneau."
        ],
        "relances": [
            "Tu cours plutôt à quel moment de la journée ?",
            "T'arrives à tenir un rythme régulier ?",
            "Qu'est-ce qui t'empêche parfois de sortir ?",
            "Tu prépares tes affaires à l'avance ?",
            "Tu cours seul ou avec quelqu'un ?",
            "T'as essayé de courir le matin ?",
            "Tu te fixes des rendez-vous running fixes ?",
            "Combien de séances tu vises par semaine ?",
            "T'as des astuces qui t'aident à rester régulier ?",
            "La flemme, ça t'arrive souvent ?"
        ]
    },
    
    # ==================== CATÉGORIE 19: AMÉLIORER L'ALLURE ====================
    # Spécifique aux questions "Comment améliorer mon allure / pace"
    "ameliorer_allure": {
        "keywords": [],  # Catégorie activée par detect_intent combiné
        "intros": [
            "Améliorer ton allure, c'est un objectif top ! 🎯",
            "Progresser sur le pace, c'est faisable avec la bonne méthode !",
            "Bonne question ! Y'a plusieurs leviers pour aller plus vite.",
            "Améliorer l'allure, c'est THE objectif de beaucoup de coureurs !",
            "Ok, on va bosser ta vitesse ! 💪",
            "Pour progresser en allure, il faut être malin dans l'entraînement.",
            "Le pace, ça se travaille ! Voici comment.",
            "Progresser sur l'allure, c'est possible à tout niveau !",
        ],
        "analyses": [
            "Ton allure actuelle de {allure}/km est {allure_comment}. Pour progresser, il faut combiner endurance de base (80% du volume) et travail spécifique (20%).",
            "Pour passer de {allure} à une allure plus rapide, le secret c'est la régularité + la patience. Compte 2-3 mois pour voir des résultats concrets.",
            "L'amélioration de l'allure vient de : 1) Plus de volume en endurance facile, 2) Séances de seuil, 3) Fractionné court.",
            "Ta cadence de {cadence} spm joue aussi un rôle. Une foulée plus rapide (170-180 spm) = moins d'effort à même allure.",
            "Pour gagner 30 sec/km, il faut environ 3-4 mois de travail structuré. C'est pas instantané mais c'est durable !",
            "Ton volume actuel ({km_semaine} km/sem) est {volume_comment}. Plus de volume facile = meilleure économie de course = allure plus rapide.",
        ],
        "conseils": [
            "Plan concret pour améliorer ton allure :\n• 1 séance de seuil/sem (ex: 3x10min à allure semi)\n• 1 séance de fractionné court (ex: 8x400m)\n• Le reste en endurance facile (Z2)",
            "Commence par ajouter du volume en endurance fondamentale. Paradoxalement, courir plus lentement sur les sorties faciles te rendra plus rapide sur les courses !",
            "Le travail de seuil est LA clé pour l'allure. Fais 2x15min ou 3x10min à ton allure semi-marathon, 1x par semaine.",
            "Pour {allure}/km → {allure_cible}/km : vise 10-12 semaines de travail avec 1 séance qualité + 2-3 sorties faciles par semaine.",
            "Travaille ta VMA avec du fractionné court (200-400m). Ça améliore ton plafond de vitesse et donc toutes tes allures.",
            "Les côtes sont géniales pour l'allure : 6-8 x 30sec en côte, récup descente. Ça booste la puissance sans traumatiser les jambes.",
        ],
        "relances": []  # Pas de relances, on utilise les suggestions
    },
    
    # ==================== CATÉGORIE 19b: AMÉLIORER L'ENDURANCE ====================
    "ameliorer_endurance": {
        "keywords": [],
        "intros": [
            "Améliorer ton endurance, excellent objectif ! 🏃",
            "L'endurance, c'est la base de tout en course à pied !",
            "Pour plus d'endurance, faut être patient mais ça paie !",
            "Progresser en endurance, c'est le meilleur investissement !",
        ],
        "analyses": [
            "L'endurance se construit avec du volume. Ton volume actuel ({km_semaine} km/sem) est {volume_comment}. Augmente progressivement (+10% max par semaine).",
            "Pour plus d'endurance, la clé c'est de courir LENTEMENT la plupart du temps. 80% de tes km doivent être en Z2 (conversation possible).",
            "Ta base d'endurance se développe sur des semaines et des mois. Pas de raccourci, mais les gains sont durables !",
            "Les sorties longues hebdomadaires (1h30-2h+) sont essentielles pour l'endurance. Tu en fais actuellement {nb_sorties_longues} par semaine.",
        ],
        "conseils": [
            "Plan pour améliorer l'endurance :\n• Augmente ton volume de 10% par semaine\n• Ajoute une sortie longue le weekend (1h30 min)\n• Reste en Z2 sur 80% des km",
            "La sortie longue est TA séance clé pour l'endurance. Commence à 1h15, monte progressivement jusqu'à 2h sur 8-10 semaines.",
            "Cours plus lentement ! Si tu peux pas tenir une conversation, c'est trop rapide pour l'endurance de base.",
            "Ajoute 1 sortie par semaine (même 30-40min facile). Le volume total compte plus que l'intensité pour l'endurance.",
        ],
        "relances": []
    },
    
    # ==================== CATÉGORIE 19c: AMÉLIORER GÉNÉRAL ====================
    "ameliorer_general": {
        "keywords": [],
        "intros": [
            "Tu veux progresser, c'est super ! 💪",
            "Améliorer tes performances, on va voir ça ensemble !",
            "La progression, c'est mon domaine ! Voyons ça.",
            "Ok, on va t'aider à progresser ! 🎯",
        ],
        "analyses": [
            "Pour progresser en course, il faut du volume (endurance), de la qualité (fractionné/seuil) et de la récup (repos, sommeil).",
            "Avec tes {nb_seances} séances et {km_semaine} km cette semaine, {analyse_progression}.",
            "La progression vient de la régularité avant tout. Mieux vaut 3 séances/sem pendant 6 mois que 5 séances/sem pendant 1 mois.",
            "Ton corps s'adapte à ce que tu lui demandes. Pour progresser, il faut varier les stimuli : endurance, tempo, VMA, côtes...",
        ],
        "conseils": [
            "Les 3 piliers de la progression :\n• Volume : plus de km (progressivement)\n• Qualité : 1-2 séances spécifiques/sem\n• Récup : repos, sommeil, nutrition",
            "Pour progresser, sois régulier ! 3 séances/sem pendant 3 mois battent 5 séances/sem pendant 1 mois.",
            "Ajoute de la variété : si tu fais toujours les mêmes séances, ton corps s'adapte et stagne.",
            "La patience est clé. Les vrais progrès prennent 3-6 mois de travail constant.",
        ],
        "relances": []
    },
    
    # ==================== CATÉGORIE 20: FALLBACK ====================
    "fallback": {
        "keywords": [],  # Pas de keywords, c'est le fallback
        "intros": [
            "Hmm, je suis pas sûr de comprendre... 🤔",
            "Je vois pas trop où tu veux en venir...",
            "Je capte pas bien, désolé !",
            "Pas sûr de suivre là...",
            "J'ai du mal à comprendre ta question...",
            "Oups, j'ai pas bien saisi...",
            "Attends, c'est quoi ta question exacte ?",
            "Je suis un peu perdu là...",
            "Tu peux m'en dire plus ?",
            "Je comprends pas bien ce que tu veux dire..."
        ],
        "analyses": [
            "Je suis ton coach running, dis-moi ce qui te tracasse côté course !",
            "Parle-moi de ton entraînement, je suis là pour ça !",
            "Côté running, je peux t'aider sur plein de sujets.",
            "Mon domaine c'est la course à pied, pose-moi tes questions là-dessus !",
            "Je suis calé sur tout ce qui touche à l'endurance et à la course.",
            "Pour le running, je suis ton gars ! Autre chose... moins.",
            "Ma spécialité c'est t'aider à progresser en course.",
            "J'ai pas compris mais dis-moi ce qui te préoccupe côté entraînement !",
            "Parlons de ta course, c'est là que je peux vraiment t'aider !",
            "Recentrons sur la course, c'est là que je peux vraiment t'aider !"
        ],
        "conseils": [
            "Essaie de me poser une question sur ton entraînement, ta forme, ou tes objectifs !",
            "Demande-moi un plan de semaine, je gère ça !",
            "Parle-moi de tes sensations, je peux analyser !",
            "Tu veux qu'on parle de ta dernière sortie ?",
            "Pose-moi une question sur ta prochaine course !",
            "On peut parler récup, nutrition, blessures... ce que tu veux !",
            "Dis-moi comment tu te sens, je te conseille !",
            "Tu veux un bilan de ta semaine ?",
            "Parle-moi de tes objectifs, je t'aide à les atteindre !",
            "Qu'est-ce qui te tracasse côté running ?"
        ],
        "relances": [
            "Tu voulais me parler de quoi exactement ?",
            "Tu peux préciser ta question ?",
            "Tu peux reformuler ?",
            "T'as une question sur ton entraînement ?",
            "Comment je peux t'aider ?",
            "Tu veux qu'on parle de ton entraînement ?",
            "Y a un sujet running qui t'intéresse ?",
            "Dis-moi ce qui te préoccupe !",
            "T'as besoin d'un conseil sur quoi ?",
            "Qu'est-ce qui t'amène aujourd'hui ?",
            "Qu'est-ce que tu veux savoir ?",
            "Je t'écoute, dis-moi tout !"
        ]
    }
}


# ============================================================
# FONCTIONS RAG (Retrieval)
# ============================================================

def get_user_training_context(workouts: List[Dict], user_goal: Optional[Dict] = None) -> Dict:
    """Extrait le contexte d'entraînement de l'utilisateur"""
    if not workouts:
        return {
            "km_semaine": 0,
            "nb_seances": 0,
            "allure": "N/A",
            "cadence": 0,
            "ratio": 1.0,
            "charge": 0,
            "zones": {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0},
            "derniere_seance": None,
            "jours_course": None
        }
    
    # Find the most recent workout date to use as reference
    # This handles test data with future dates (2026)
    most_recent_date = None
    for w in workouts:
        try:
            w_date = w.get("date")
            if isinstance(w_date, str):
                if "T" in w_date:
                    w_date = datetime.fromisoformat(w_date.replace("Z", "+00:00"))
                else:
                    w_date = datetime.fromisoformat(w_date + "T23:59:59+00:00")
            if w_date and (most_recent_date is None or w_date > most_recent_date):
                most_recent_date = w_date
        except:
            continue
    
    # Fall back to current time if no valid dates found
    now = most_recent_date if most_recent_date else datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    
    recent_workouts = []
    for w in workouts:
        try:
            w_date = w.get("date")
            if isinstance(w_date, str):
                if "T" in w_date:
                    w_date = datetime.fromisoformat(w_date.replace("Z", "+00:00"))
                else:
                    w_date = datetime.fromisoformat(w_date + "T00:00:00+00:00")
            if w_date and w_date >= week_ago:
                recent_workouts.append(w)
        except:
            continue
    
    # Stats semaine
    km_semaine = sum(w.get("distance_km", 0) for w in recent_workouts)
    nb_seances = len(recent_workouts)
    
    # Allure moyenne
    paces = [w.get("avg_pace_min_km") for w in recent_workouts if w.get("avg_pace_min_km")]
    if paces:
        avg_pace = sum(paces) / len(paces)
        pace_min = int(avg_pace)
        pace_sec = int((avg_pace - pace_min) * 60)
        allure = f"{pace_min}:{pace_sec:02d}"
    else:
        allure = "N/A"
    
    # Cadence moyenne
    cadences = [w.get("avg_cadence_spm") for w in recent_workouts if w.get("avg_cadence_spm")]
    cadence = int(sum(cadences) / len(cadences)) if cadences else 0
    
    # Zones (moyenne)
    zones = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
    zone_count = 0
    for w in recent_workouts:
        if w.get("effort_zone_distribution"):
            for z in zones:
                zones[z] += w["effort_zone_distribution"].get(z, 0)
            zone_count += 1
    if zone_count > 0:
        zones = {z: round(v / zone_count) for z, v in zones.items()}
    
    # Ratio charge/récup (simplifié)
    km_total_30j = sum(w.get("distance_km", 0) for w in workouts[:30])
    km_moyen = km_total_30j / 4 if workouts else 0
    ratio = round(km_semaine / km_moyen, 2) if km_moyen > 0 else 1.0
    
    # Charge (km * intensité approximative)
    charge = round(km_semaine * (1 + (zones.get("z4", 0) + zones.get("z5", 0)) / 100), 1)
    
    # Dernière séance
    derniere = workouts[0] if workouts else None
    
    # Jours jusqu'à la course (si objectif)
    jours_course = None
    if user_goal and user_goal.get("event_date"):
        try:
            event_date = user_goal["event_date"]
            if isinstance(event_date, str):
                event_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            # Use most_recent_date as reference for test data
            reference_date = most_recent_date if most_recent_date else datetime.now(timezone.utc)
            jours_course = (event_date - reference_date).days
            if jours_course < 0:
                jours_course = None  # Course passée
        except:
            pass
    
    return {
        "km_semaine": round(km_semaine, 1),
        "nb_seances": nb_seances,
        "allure": allure,
        "cadence": cadence,
        "ratio": ratio,
        "charge": charge,
        "zones": zones,
        "derniere_seance": derniere,
        "jours_course": jours_course,
        "km_total": round(sum(w.get("distance_km", 0) for w in workouts), 1)
    }


def get_relevant_knowledge(category: str, context: Dict) -> List[str]:
    """Récupère les conseils pertinents de la base de connaissances"""
    tips = []
    
    # Catégorie principale
    if category in KNOWLEDGE_BASE:
        tips.extend(random.sample(KNOWLEDGE_BASE[category]["tips"], min(3, len(KNOWLEDGE_BASE[category]["tips"]))))
    
    # Tips conditionnels basés sur le contexte
    if context.get("ratio", 1.0) > 1.3:
        if "recuperation" in KNOWLEDGE_BASE:
            tips.append(random.choice(KNOWLEDGE_BASE["recuperation"]["tips"]))
    
    if context.get("cadence", 180) < 165:
        if "allure_cadence" in KNOWLEDGE_BASE:
            tips.append(random.choice(KNOWLEDGE_BASE["allure_cadence"]["tips"]))
    
    return tips[:5]  # Max 5 tips


# ============================================================
# DÉTECTION D'INTENTION
# ============================================================

# Réponses courtes qui indiquent une réponse à une question précédente
# NOTE: Plus de "relance" - les suggestions intelligentes remplacent les relances
SHORT_RESPONSES = {
    # SALUTATIONS
    "salut": {
        "response": "Salut ! 👋 Content de te voir ! Je suis là pour t'aider sur ton entraînement, ta récup, tes objectifs...",
    },
    "bonjour": {
        "response": "Bonjour ! ☀️ Prêt à parler running ? Je peux t'aider sur ton plan, ta récup, tes zones...",
    },
    "hello": {
        "response": "Hello ! 👋 Je suis ton coach running. Dis-moi ce qui te préoccupe !",
    },
    "hey": {
        "response": "Hey ! 🙌 Quoi de neuf côté running ?",
    },
    "coucou": {
        "response": "Coucou ! 😊 Comment ça va ? Je suis là pour t'aider sur ton entraînement.",
    },
    "bonsoir": {
        "response": "Bonsoir ! 🌙 Tu veux qu'on parle de ton entraînement ou de ta récup ?",
    },
    "hi": {
        "response": "Hi ! 👋 Je suis ton coach. Parle-moi de ton entraînement !",
    },
    "yo": {
        "response": "Yo ! 🤙 Prêt à bosser ?",
    },
    # Réponses temporelles (matin/soir)
    "matin": {
        "response": "Le matin, c'est top pour l'énergie et la fraîcheur ! 🌅 Tu peux prévoir ton fractionné le matin quand t'es bien réveillé. Pour les sorties longues, ça laisse le reste de la journée libre !",
    },
    "soir": {
        "response": "Le soir, c'est parfait pour décompresser après la journée ! 🌆 Les muscles sont plus souples et la perf est souvent meilleure. Par contre, évite les séances trop intenses juste avant de dormir.",
    },
    "midi": {
        "response": "Le midi, c'est bien si t'as une pause assez longue ! ☀️ Avantage : ça coupe la journée et te donne de l'énergie pour l'après-midi. Juste, mange léger avant.",
    },
    # Réponses oui/non (français ET anglais)
    "oui": {
        "response": "Super, on est partis ! 💪 Je suis là pour t'aider.",
    },
    "yes": {
        "response": "Super, on est partis ! 💪 Je suis là pour t'aider.",
    },
    "ouais": {
        "response": "Parfait ! 👊 On continue.",
    },
    "yep": {
        "response": "Top ! 👍 Je t'écoute.",
    },
    "non": {
        "response": "Pas de souci, on adapte ! 👍",
    },
    "no": {
        "response": "Pas de souci, on adapte ! 👍",
    },
    "nope": {
        "response": "Ok, pas de problème !",
    },
    "ok": {
        "response": "Parfait ! ✅",
    },
    "okay": {
        "response": "Parfait ! ✅",
    },
    "d'accord": {
        "response": "Super ! 👌",
    },
    "merci": {
        "response": "De rien, c'est le job ! 😊 Content de pouvoir t'aider.",
    },
    "thanks": {
        "response": "De rien ! 😊 Je suis là pour ça.",
    },
    "cool": {
        "response": "Content que ça te plaise ! 😎",
    },
    "parfait": {
        "response": "Super ! On est sur la bonne voie. 🎯",
    },
    "perfect": {
        "response": "Super ! 🎯",
    },
    "génial": {
        "response": "Content que ça te convienne ! 🙌",
    },
    "top": {
        "response": "Au top ! 🔥",
    },
    "nickel": {
        "response": "Nickel ! 👌",
    },
    # Jours de la semaine
    "lundi": {"response": "Lundi, bonne idée pour bien démarrer la semaine ! 📅 C'est souvent un bon jour pour une séance de reprise."},
    "mardi": {"response": "Mardi, c'est souvent un bon jour pour du fractionné ! 💨 Les jambes sont bien récupérées du week-end."},
    "mercredi": {"response": "Mercredi, milieu de semaine, parfait pour une séance qualité ! 🎯"},
    "jeudi": {"response": "Jeudi, jour idéal pour une séance technique ou un footing récup. 🤔"},
    "vendredi": {"response": "Vendredi, on prépare le week-end ! 🏃 Séance légère pour être frais."},
    "samedi": {"response": "Samedi, journée idéale pour la sortie longue ! ☀️ Profite du temps libre."},
    "dimanche": {"response": "Dimanche, jour classique pour la sortie longue ou repos ! 🌳"},
}


def detect_intent(message: str) -> Tuple[str, float]:
    """Détecte l'intention/catégorie du message avec compréhension du type de question"""
    message_lower = message.lower()
    
    # ============================================================
    # ÉTAPE 1: Détecter le TYPE de question (améliorer, analyser, etc.)
    # ============================================================
    question_type = "general"
    
    # Détection des questions "comment améliorer / progresser"
    ameliorer_keywords = ["améliorer", "ameliorer", "progresser", "augmenter", "booster", "optimiser", "gagner", "passer de", "passer à", "descendre", "baisser mon"]
    if any(kw in message_lower for kw in ameliorer_keywords):
        question_type = "ameliorer"
    
    # Détection des questions d'analyse/bilan
    analyse_keywords = ["analyse", "bilan", "comment va", "où j'en suis", "mon niveau", "ma forme"]
    if any(kw in message_lower for kw in analyse_keywords):
        question_type = "analyse"
    
    # Détection des questions de conseil
    conseil_keywords = ["conseil", "recommand", "que faire", "quoi faire", "tu me conseilles", "tu penses"]
    if any(kw in message_lower for kw in conseil_keywords):
        question_type = "conseil"
    
    # ============================================================
    # ÉTAPE 2: Détecter le SUJET (allure, fatigue, récup, etc.)
    # ============================================================
    best_category = "fallback"
    best_score = 0
    
    for category, data in TEMPLATES.items():
        if category == "fallback":
            continue
            
        keywords = data.get("keywords", [])
        score = 0
        
        for keyword in keywords:
            if keyword in message_lower:
                # Score plus élevé pour les mots exacts
                score += 2
                # Bonus pour les mots en début de message
                if message_lower.startswith(keyword) or message_lower.startswith(keyword[:3]):
                    score += 1
        
        if score > best_score:
            best_score = score
            best_category = category
    
    # ============================================================
    # ÉTAPE 3: Combiner type + sujet pour une catégorie finale
    # ============================================================
    
    # Si c'est une question d'amélioration sur l'allure/cadence
    if question_type == "ameliorer" and best_category == "allure_cadence":
        return "ameliorer_allure", 0.9
    
    # Si c'est une question d'amélioration sur l'endurance/plan
    if question_type == "ameliorer" and best_category in ["plan", "semaine"]:
        return "ameliorer_endurance", 0.9
    
    # Si c'est une question d'amélioration générale
    if question_type == "ameliorer" and best_score < 2:
        return "ameliorer_general", 0.8
    
    # Seuil minimum pour éviter les faux positifs
    confidence = min(best_score / 4, 1.0) if best_score > 0 else 0
    
    return best_category, confidence


# ============================================================
# GÉNÉRATION DE RÉPONSE (100% déterministe, templates + random)
# ============================================================

def _get_zones_verdict(zones: Dict) -> str:
    """Génère un verdict sur la répartition des zones"""
    z1z2 = zones.get("z1", 0) + zones.get("z2", 0)
    z3 = zones.get("z3", 0)
    z4z5 = zones.get("z4", 0) + zones.get("z5", 0)
    
    if z1z2 >= 60:
        return "Très bonne base d'endurance, continue comme ça !"
    elif z1z2 >= 40:
        return "Bon équilibre entre endurance et intensité."
    elif z3 >= 50:
        return "Beaucoup de tempo, pense à faire plus d'endurance fondamentale."
    elif z4z5 >= 30:
        return "Pas mal d'intensité ! Assure-toi de bien récupérer."
    else:
        return "Continue à varier tes séances !"


def _get_sensations(context: Dict) -> str:
    """Génère une description des sensations basée sur le contexte"""
    ratio = context.get("ratio", 1.0)
    nb_seances = context.get("nb_seances", 0)
    z4z5 = context.get("zones", {}).get("z4", 0) + context.get("zones", {}).get("z5", 0)
    
    if ratio > 1.5:
        return "peut-être un peu lourdes avec cette charge élevée"
    elif ratio > 1.2:
        return "correctes mais surveillées vu la charge"
    elif nb_seances >= 4:
        return "bonnes grâce à ta régularité"
    elif z4z5 > 25:
        return "intenses avec ce travail de qualité"
    else:
        return "plutôt bonnes cette semaine"


def _get_sensations_conseil(context: Dict) -> str:
    """Génère un conseil basé sur les sensations estimées"""
    ratio = context.get("ratio", 1.0)
    z4z5 = context.get("zones", {}).get("z4", 0) + context.get("zones", {}).get("z5", 0)
    
    if ratio > 1.5:
        return "Prends une semaine plus cool pour récupérer."
    elif ratio > 1.2:
        return "Écoute bien ton corps cette semaine."
    elif z4z5 > 25:
        return "Bien joué sur l'intensité, récupère bien entre les séances."
    else:
        return "Continue sur cette lancée !"


def _get_point_fort(context: Dict) -> str:
    """Identifie le point fort de la semaine"""
    zones = context.get("zones", {})
    z1z2 = zones.get("z1", 0) + zones.get("z2", 0)
    nb_seances = context.get("nb_seances", 0)
    cadence = context.get("cadence", 0)
    
    if nb_seances >= 4:
        return "ta régularité"
    elif z1z2 >= 50:
        return "ton travail en endurance"
    elif cadence >= 170:
        return "ta cadence de course"
    elif context.get("km_semaine", 0) >= 30:
        return "ton volume d'entraînement"
    else:
        return "ta motivation à continuer"


def _get_point_ameliorer(context: Dict) -> str:
    """Identifie le point à améliorer"""
    zones = context.get("zones", {})
    z1z2 = zones.get("z1", 0) + zones.get("z2", 0)
    z3 = zones.get("z3", 0)
    cadence = context.get("cadence", 0)
    nb_seances = context.get("nb_seances", 0)
    
    if z1z2 < 30 and z3 > 50:
        return "ajouter plus d'endurance fondamentale"
    elif 0 < cadence < 165:
        return "travailler ta cadence"
    elif nb_seances < 3:
        return "augmenter la fréquence des séances"
    else:
        return "varier les types de séances"


def _get_conseil_semaine_prochaine(context: Dict) -> str:
    """Génère un conseil pour la semaine prochaine"""
    zones = context.get("zones", {})
    z1z2 = zones.get("z1", 0) + zones.get("z2", 0)
    z3 = zones.get("z3", 0)
    ratio = context.get("ratio", 1.0)
    nb_seances = context.get("nb_seances", 0)
    cadence = context.get("cadence", 0)
    
    conseils = []
    
    if ratio > 1.3:
        conseils.append("réduire un peu le volume pour mieux récupérer")
    elif ratio < 0.8:
        conseils.append("augmenter légèrement le volume")
    
    if z1z2 < 30 and z3 > 50:
        conseils.append("ajouter une sortie longue en endurance fondamentale")
    
    if 0 < cadence < 165:
        conseils.append("intégrer des gammes ou du travail technique")
    
    if nb_seances < 3:
        conseils.append("ajouter une séance de plus si ton emploi du temps le permet")
    
    if not conseils:
        conseils = [
            "maintenir ce bon équilibre",
            "continuer sur cette lancée",
            "garder cette régularité"
        ]
    
    return random.choice(conseils) if len(conseils) == 1 else conseils[0]


def _get_resume_global(context: Dict) -> str:
    """Génère un résumé global de la semaine"""
    km = context.get("km_semaine", 0)
    nb = context.get("nb_seances", 0)
    ratio = context.get("ratio", 1.0)
    
    if nb >= 4 and km >= 30:
        return "semaine très active"
    elif nb >= 3:
        return "bonne semaine"
    elif ratio > 1.3:
        return "semaine chargée"
    elif nb == 0:
        return "semaine de repos"
    else:
        return "semaine correcte"


def _get_conseil_global(context: Dict) -> str:
    """Génère un conseil global"""
    zones = context.get("zones", {})
    z1z2 = zones.get("z1", 0) + zones.get("z2", 0)
    ratio = context.get("ratio", 1.0)
    
    if ratio > 1.3:
        return "Pense à bien récupérer."
    elif z1z2 < 30:
        return "Ajoute plus d'endurance fondamentale."
    else:
        return "Continue comme ça !"


def _get_recup_besoin(context: Dict) -> str:
    """Génère le besoin en récupération"""
    ratio = context.get("ratio", 1.0)
    km = context.get("km_semaine", 0)
    nb = context.get("nb_seances", 0)
    
    if ratio > 1.5:
        return "plusieurs jours de repos ou récup très légère"
    elif ratio > 1.2:
        return "au moins 2 jours de récup active"
    elif km >= 40:
        return "1-2 jours de récup active entre les grosses séances"
    elif nb >= 4:
        return "bien alterner effort et récup"
    else:
        return "maintenir un bon équilibre effort/repos"


def _get_recup_conseil(context: Dict) -> str:
    """Génère un conseil de récupération"""
    ratio = context.get("ratio", 1.0)
    
    conseils = [
        "Hydrate-toi bien et dors suffisamment.",
        "Le foam roller peut aider à détendre les muscles.",
        "Une marche légère aide à récupérer activement.",
        "Les étirements doux après chaque sortie aident.",
        "Le sommeil est ton meilleur allié pour récupérer."
    ]
    
    if ratio > 1.3:
        conseils.insert(0, "Cette semaine, privilégie le repos.")
    
    return random.choice(conseils)


def fill_template(template: str, context: Dict) -> str:
    """Remplit un template avec les données du contexte"""
    # Créer un dictionnaire de remplacement avec des valeurs par défaut
    replacements = {
        "km_semaine": str(context.get("km_semaine", 0)),
        "nb_seances": str(context.get("nb_seances", 0)),
        "allure": context.get("allure", "N/A"),
        "cadence": str(context.get("cadence", 0)),
        "ratio": str(context.get("ratio", 1.0)),
        "charge": str(context.get("charge", 0)),
        "decrochage": str(random.randint(5, 15)),
        "jours_course": str(context.get("jours_course", "N/A")),
        "z1z2": str(context.get("zones", {}).get("z1", 0) + context.get("zones", {}).get("z2", 0)),
        "z3": str(context.get("zones", {}).get("z3", 0)),
        "z4z5": str(context.get("zones", {}).get("z4", 0) + context.get("zones", {}).get("z5", 0)),
        "km_total": str(context.get("km_total", 0)),
        
        # Commentaires contextuels
        "cadence_comment": "c'est dans la bonne zone !" if context.get("cadence", 170) >= 170 else "c'est un peu bas, on peut améliorer ça.",
        "ratio_comment": "c'est équilibré, nickel !" if context.get("ratio", 1.0) <= 1.2 else "c'est un peu élevé, pense à récupérer.",
        "allure_comment": "solide" if context.get("allure", "N/A") != "N/A" else "N/A",
        "appreciation": "Belle semaine !" if context.get("nb_seances", 0) >= 3 else "C'est un bon début !",
        
        # Sensations (basées sur le ratio et le volume)
        "sensations": _get_sensations(context),
        "sensations_conseil": _get_sensations_conseil(context),
        
        # Comparaison semaine
        "comparaison_km": "stable" if context.get("ratio", 1.0) <= 1.1 else ("en hausse" if context.get("ratio", 1.0) > 1.1 else "en baisse"),
        "comparaison_intensite": "similaire" if context.get("zones", {}).get("z4", 0) + context.get("zones", {}).get("z5", 0) < 20 else "plus intense",
        
        # Charge et évolution
        "charge_niveau": "modérée" if context.get("ratio", 1.0) <= 1.2 else "élevée",
        "charge_interpretation": "tu peux continuer comme ça" if context.get("ratio", 1.0) <= 1.2 else "attention à bien récupérer",
        "allure_evolution": "stable" if context.get("ratio", 1.0) <= 1.1 else "en progression",
        
        # Régularité et répartition
        "nb_jours": str(context.get("nb_seances", 0)),
        "regularite_comment": "Bonne régularité !" if context.get("nb_seances", 0) >= 3 else "Tu peux ajouter une séance si tu te sens bien.",
        "repartition_types": "équilibrée" if context.get("zones", {}).get("z2", 0) > 30 else "orientée intensité",
        "repartition_verdict": "Continue comme ça !" if context.get("zones", {}).get("z2", 0) > 30 else "Ajoute plus d'endurance fondamentale.",
        
        # Points forts/faibles
        "point_fort": _get_point_fort(context),
        "point_ameliorer": _get_point_ameliorer(context),
        
        # Conseil semaine prochaine
        "conseil_semaine_prochaine": _get_conseil_semaine_prochaine(context),
        
        # Résumé global
        "resume_global": _get_resume_global(context),
        "conseil_global": _get_conseil_global(context),
        
        # Récupération
        "recup_besoin": _get_recup_besoin(context),
        "recup_conseil": _get_recup_conseil(context),
        
        # Commentaires contextuels supplémentaires
        "zones_resume": f"Z1-Z2: {context.get('zones', {}).get('z1', 0) + context.get('zones', {}).get('z2', 0)}%, Z3: {context.get('zones', {}).get('z3', 0)}%, Z4-Z5: {context.get('zones', {}).get('z4', 0) + context.get('zones', {}).get('z5', 0)}%" if context.get("zones") else "pas de données de zones",
        "zones_conseil": "bon équilibre !" if context.get("zones", {}).get("z2", 0) > 40 else "pense à faire plus d'endurance fondamentale.",
        "zones_verdict": _get_zones_verdict(context.get("zones", {})),
        "charge_recommandation": "tu peux maintenir ou légèrement augmenter" if context.get("ratio", 1.0) <= 1.2 else "calme un peu le jeu cette semaine",
        "adaptation_comment": "c'est une bonne base à maintenir" if context.get("km_semaine", 0) > 0 else "on démarre doucement",
        "repartition": "correcte" if context.get("zones", {}).get("z2", 0) > 30 else "à ajuster",
        "repartition_comment": "Continue comme ça !",
        "ratio_implication": "tu peux y aller" if context.get("ratio", 1.0) <= 1.2 else "récupère un peu d'abord",
        "progression": "une bonne régularité" if context.get("nb_seances", 0) >= 2 else "une marge de progression",
        "progression_action": "consolider cette base" if context.get("nb_seances", 0) >= 2 else "augmenter le volume progressivement",
    }
    
    # Remplacer les placeholders
    result = template
    for key, value in replacements.items():
        result = result.replace("{" + key + "}", value)
    
    # Nettoyer les placeholders non remplacés
    import re
    result = re.sub(r'\{[^}]+\}', '', result)
    
    return result


def generate_response(message: str, context: Dict, category: str = None) -> str:
    """Génère une réponse complète basée sur le message et le contexte"""
    
    # D'abord, vérifier si c'est une réponse courte (réponse à une question précédente)
    message_lower = message.lower().strip()
    
    # Vérifier les réponses courtes connues
    for key, response_data in SHORT_RESPONSES.items():
        if message_lower == key or message_lower.startswith(key + " ") or message_lower.endswith(" " + key):
            return f"{response_data['response']}\n\n{response_data['relance']}"
    
    # Si le message est très court (< 15 caractères) et pas reconnu, être plus accueillant
    if len(message_lower) < 15 and not any(kw in message_lower for cat in TEMPLATES.values() for kw in cat.get("keywords", [])):
        # Réponse générique pour les messages courts non reconnus
        short_responses = [
            f"J'ai pas bien compris \"{message}\" 🤔 Tu peux me donner plus de détails ?",
            f"Hmm, \"{message}\"... tu veux dire quoi exactement ?",
            f"Je suis pas sûr de comprendre. Tu parles de ton entraînement ?",
            f"Peux-tu préciser un peu ? Je suis là pour t'aider sur la course ! 🏃",
        ]
        return random.choice(short_responses)
    
    # Détection d'intention si pas de catégorie fournie
    if not category:
        category, confidence = detect_intent(message)
    
    # Récupérer les templates de la catégorie
    templates = TEMPLATES.get(category, TEMPLATES["fallback"])
    
    # Sélection aléatoire de chaque bloc (SANS les relances)
    intro = random.choice(templates["intros"])
    analyse = random.choice(templates["analyses"])
    conseil = random.choice(templates["conseils"])
    # NOTE: Plus de relance - les suggestions remplacent les relances
    
    # Remplir les templates avec le contexte
    intro = fill_template(intro, context)
    analyse = fill_template(analyse, context)
    conseil = fill_template(conseil, context)
    
    # Ajouts conditionnels
    extras = []
    
    # Si ratio élevé, insister sur la récup
    if context.get("ratio", 1.0) > 1.5:
        extras.append("⚠️ Attention, ton ratio charge/récup est élevé. Priorise le repos cette semaine !")
    
    # Si cadence basse
    if 0 < context.get("cadence", 180) < 165:
        extras.append("💡 Ta cadence est un peu basse. Pense aux gammes et aux côtes pour l'améliorer naturellement.")
    
    # Si course proche
    if context.get("jours_course") and context["jours_course"] <= 14:
        objectif = context.get("objectif_nom", "ta course")
        extras.append(f"🎯 Plus que {context['jours_course']} jours avant {objectif} ! On est dans la dernière ligne droite.")
    
    # Assemblage final (SANS relance à la fin)
    parts = [intro, "", analyse]
    
    if extras:
        parts.extend(["", " ".join(extras)])
    
    parts.extend(["", conseil])
    
    # RAG: Intégrer un tip de la knowledge base si disponible
    rag_tips = context.get("rag_tips", [])
    if rag_tips:
        # Sélectionner un tip pertinent et l'intégrer
        tip = random.choice(rag_tips)
        parts.extend(["", f"💡 {tip}"])
    
    return "\n".join(parts).strip()


# ============================================================
# SUGGESTIONS INTELLIGENTES (Questions que l'USER peut poser au COACH)
# 3-5 questions par réponse, personnalisées avec les données user
# ============================================================

SUGGESTED_QUESTIONS = {
    # ==================== FATIGUE / LOURDEUR ====================
    "fatigue": [
        "Comment mieux récupérer demain ?",
        "Conseils pour éviter la lourdeur en fin de sortie ?",
        "Comment gérer une charge élevée comme celle-là ?",
        "Quel type de footing pour recharger les batteries ?",
        "Comment savoir si je suis en surcharge ?",
        "Quels signes de fatigue surveiller ?",
        "Combien de jours de repos après une grosse semaine ?",
        "Comment optimiser mon sommeil pour mieux récupérer ?",
        "Quelle nutrition pour mieux récupérer ?",
        "Est-ce que je dois réduire le volume cette semaine ?",
        "Comment éviter le surentraînement ?",
        "Quels étirements pour soulager les jambes lourdes ?",
    ],
    
    # ==================== ALLURE / CADENCE ====================
    "allure_cadence": [
        "Comment augmenter ma cadence efficacement ?",
        "Quels drills pour booster ma foulée ?",
        "Quelle allure cible pour mon prochain tempo ?",
        "Comment progresser sur mon allure moyenne ?",
        "Comment améliorer ma technique de course ?",
        "Quels exercices pour une foulée plus économe ?",
        "Comment trouver ma bonne allure en endurance ?",
        "Quelle cadence viser pour progresser ?",
        "Comment travailler ma vitesse sans me blesser ?",
        "Quels gammes faire avant une séance rapide ?",
        "Comment interpréter mes zones cardiaques ?",
        "Quelle est l'allure idéale pour une sortie longue ?",
    ],
    
    # ==================== PLAN / PRÉPA COURSE ====================
    "plan": [
        "Quel plan pour la semaine prochaine ?",
        "Comment augmenter le volume sans risque ?",
        "Comment adapter le plan si je me sens fatigué ?",
        "Combien de séances par semaine idéalement ?",
        "Comment équilibrer fractionné et endurance ?",
        "Quelle progression de volume est sécuritaire ?",
        "Comment planifier une semaine type ?",
        "Quand placer ma sortie longue dans la semaine ?",
        "Comment intégrer du renforcement musculaire ?",
        "Quelle est la meilleure répartition des séances ?",
        "Comment gérer une semaine chargée au travail ?",
        "Quand faire une semaine de récupération ?",
    ],
    
    # ==================== PRÉPA COURSE (proche) ====================
    "prepa_course": [
        "Comment bien préparer ma course ?",
        "Quelle stratégie d'allure adopter ?",
        "Que manger avant la course ?",
        "Comment gérer le stress d'avant-course ?",
        "Quoi faire la dernière semaine avant ?",
        "Comment m'échauffer le jour J ?",
        "Quelle stratégie pour les ravitaillements ?",
        "Comment éviter de partir trop vite ?",
        "Quels objectifs réalistes me fixer ?",
        "Comment gérer le dénivelé sur ce parcours ?",
        "Que faire si je me sens pas bien le jour J ?",
        "Comment récupérer après la course ?",
    ],
    
    # ==================== RÉCUPÉRATION / REPOS ====================
    "recuperation": [
        "Conseils pour mieux dormir et récupérer ?",
        "Comment optimiser ma récup après une semaine chargée ?",
        "Quelle séance de mobilité ajouter ?",
        "Est-ce que je dois prendre un jour off complet ?",
        "Quels étirements faire après une sortie ?",
        "Comment utiliser le foam roller efficacement ?",
        "Bain froid ou chaud pour la récup ?",
        "Quelle alimentation favorise la récupération ?",
        "Comment savoir si j'ai bien récupéré ?",
        "Combien de temps entre deux séances intenses ?",
        "Comment récupérer d'une course difficile ?",
        "Quels compléments pour mieux récupérer ?",
    ],
    
    # ==================== ANALYSE SEMAINE ====================
    "analyse_semaine": [
        "Comment interpréter mes stats de la semaine ?",
        "Est-ce que ma répartition de zones est bonne ?",
        "Comment améliorer ma régularité ?",
        "Qu'est-ce que je pourrais faire mieux ?",
        "Comment comparer avec la semaine dernière ?",
        "Mon volume est-il suffisant pour progresser ?",
        "Comment lire mon ratio charge/récup ?",
        "Quels sont mes points forts actuels ?",
        "Sur quoi devrais-je travailler en priorité ?",
        "Ma progression est-elle normale ?",
        "Comment atteindre mes objectifs plus vite ?",
        "Quelles erreurs éviter pour la suite ?",
    ],
    
    # ==================== MOTIVATION ====================
    "motivation": [
        "Comment rester motivé sur la durée ?",
        "Petit défi fun pour la prochaine sortie ?",
        "Comment gérer les baisses de motivation ?",
        "Quoi faire quand j'ai pas envie de courir ?",
        "Comment me fixer des objectifs motivants ?",
        "Comment varier mes parcours pour pas m'ennuyer ?",
        "Courir seul ou en groupe, qu'est-ce qui est mieux ?",
        "Comment transformer une mauvaise sortie en positif ?",
        "Comment célébrer mes petites victoires ?",
        "Comment garder l'envie après un échec ?",
        "Quels podcasts ou musiques pour courir ?",
        "Comment me remotiver après une pause ?",
    ],
    
    # ==================== BLESSURES ====================
    "blessures": [
        "Que faire pour une douleur au genou ?",
        "Dois-je continuer ou me reposer avec cette douleur ?",
        "Conseils pour éviter que ça empire ?",
        "Quels exercices de renforcement préventif ?",
        "Comment reprendre après une blessure ?",
        "Quand consulter un médecin du sport ?",
        "Comment prévenir les blessures courantes ?",
        "Quels signes indiquent qu'il faut s'arrêter ?",
        "Comment adapter mon entraînement avec une gêne ?",
        "Quels étirements pour prévenir les douleurs ?",
        "Comment renforcer mes points faibles ?",
        "Quelle est la différence entre courbature et blessure ?",
    ],
    
    # ==================== PROGRESSION / STAGNATION ====================
    "progression": [
        "Comment casser un plateau de progression ?",
        "Pourquoi je ne progresse plus ?",
        "Comment varier mes entraînements pour progresser ?",
        "Quelle est ma VMA estimée ?",
        "Comment travailler ma vitesse efficacement ?",
        "Quels types de séances pour progresser vite ?",
        "Comment savoir si je progresse vraiment ?",
        "Quel volume pour passer au niveau supérieur ?",
        "Comment améliorer mon endurance fondamentale ?",
        "Quels indicateurs de progression surveiller ?",
        "Comment éviter de stagner dans mon entraînement ?",
        "Quels objectifs intermédiaires me fixer ?",
    ],
    
    # ==================== NUTRITION ====================
    "nutrition": [
        "Quoi manger avant une sortie longue ?",
        "Comment bien m'hydrater pendant l'effort ?",
        "Quels gels ou barres recommandes-tu ?",
        "Comment éviter les problèmes digestifs en courant ?",
        "Que manger après une séance intense ?",
        "Comment adapter mon alimentation à mon entraînement ?",
        "Quels aliments favorisent la récupération ?",
        "Comment gérer la nutrition en course longue ?",
        "Petit-déjeuner idéal avant une course ?",
        "Comment éviter les crampes ?",
        "Faut-il prendre des compléments alimentaires ?",
        "Combien boire par jour quand on s'entraîne ?",
    ],
    
    # ==================== ÉQUIPEMENT ====================
    "equipement": [
        "Quand changer mes chaussures de running ?",
        "Comment choisir ma prochaine paire de chaussures ?",
        "Quel équipement pour courir sous la pluie ?",
        "Comment éviter les ampoules ?",
        "Quelle montre GPS recommandes-tu ?",
        "Quels vêtements techniques privilégier ?",
        "Comment entretenir mes chaussures de running ?",
        "Quel équipement pour le trail ?",
        "Comment choisir mes chaussettes de course ?",
        "Faut-il des chaussures différentes selon le terrain ?",
        "Comment habiller pour courir par grand froid ?",
        "Quels accessoires vraiment utiles pour courir ?",
    ],
    
    # ==================== GÉNÉRAL / FALLBACK ====================
    "general": [
        "Analyse ma dernière sortie ?",
        "Conseil pour ma récup globale ?",
        "Plan pour la semaine prochaine ?",
        "Comment progresser sur mon allure ?",
        "Comment améliorer ma technique de course ?",
        "Quels objectifs me fixer ?",
        "Comment équilibrer vie perso et entraînement ?",
        "Quels sont mes axes de progression ?",
        "Comment me préparer pour ma prochaine course ?",
        "Comment interpréter mes données d'entraînement ?",
        "Quels conseils pour un coureur de mon niveau ?",
        "Comment structurer ma semaine d'entraînement ?",
    ],
    
    # ==================== FALLBACK ====================
    "fallback": [
        "Comment améliorer ma récup ?",
        "Plan pour la semaine prochaine ?",
        "Comment progresser en course à pied ?",
        "Analyse de ma dernière séance ?",
        "Conseils pour éviter les blessures ?",
        "Comment augmenter mon volume ?",
        "Quelle séance faire demain ?",
        "Comment améliorer ma cadence ?",
        "Quels exercices de renforcement faire ?",
        "Comment mieux gérer mes zones cardiaques ?",
        "Conseils nutrition pour coureur ?",
        "Comment rester motivé ?",
    ],
}

# Mapping des catégories vers leurs suggestions
CATEGORY_SUGGESTION_MAP = {
    "fatigue": "fatigue",
    "allure_cadence": "allure_cadence",
    "recuperation": "recuperation",
    "plan": "plan",
    "prepa_course": "prepa_course",
    "analyse_semaine": "analyse_semaine",
    "motivation": "motivation",
    "blessures": "blessures",
    "progression": "progression",
    "nutrition": "nutrition",
    "equipement": "equipement",
    "meteo": "general",
    "mental": "motivation",
    "sommeil": "recuperation",
    "renforcement": "blessures",
    "chaleur": "general",
    "post_course": "recuperation",
    "habitudes": "general",
    "general": "general",
    "fallback": "fallback",
}


def get_personalized_suggestions(category: str, context: Dict, num_suggestions: int = 4) -> List[str]:
    """
    Génère 3-5 suggestions personnalisées (questions que l'USER peut poser au COACH).
    Personnalise avec les données user quand disponibles.
    """
    # Récupérer la catégorie de suggestions
    suggestion_category = CATEGORY_SUGGESTION_MAP.get(category, "fallback")
    base_suggestions = SUGGESTED_QUESTIONS.get(suggestion_category, SUGGESTED_QUESTIONS["fallback"])
    
    # Créer une liste de suggestions personnalisées
    personalized = []
    
    # Extraire le contexte utilisateur
    jours_course = context.get("jours_course")
    objectif = context.get("objectif_nom", "")
    cadence = context.get("cadence", 0)
    ratio = context.get("ratio", 1.0)
    km_semaine = context.get("km_semaine", 0)
    nb_seances = context.get("nb_seances", 0)
    allure = context.get("allure", "")
    zones = context.get("zones", {})
    
    # Suggestions personnalisées basées sur le contexte
    
    # Si course proche avec objectif défini
    if jours_course and jours_course > 0 and jours_course <= 30:
        if objectif:
            personalized.append(f"Comment bien préparer {objectif} ?")
            if jours_course <= 7:
                personalized.append(f"Quoi faire cette dernière semaine avant {objectif} ?")
            elif jours_course <= 14:
                personalized.append(f"Comment gérer les {jours_course} derniers jours avant {objectif} ?")
        else:
            personalized.append(f"Comment préparer ma course dans {jours_course} jours ?")
    
    # Si cadence basse (< 165)
    if 0 < cadence < 165:
        personalized.append("Comment améliorer ma cadence de course ?")
        personalized.append("Quels drills pour augmenter ma cadence ?")
    
    # Si ratio élevé (surcharge)
    if ratio > 1.3:
        personalized.append("Comment mieux récupérer cette semaine ?")
        personalized.append("Dois-je réduire le volume ?")
    
    # Si beaucoup de Z3 (tempo) et peu de Z1-Z2 (endurance)
    z1z2 = zones.get("z1", 0) + zones.get("z2", 0)
    z3 = zones.get("z3", 0)
    if z3 > 50 and z1z2 < 30:
        personalized.append("Comment équilibrer mes zones d'entraînement ?")
        personalized.append("Comment travailler plus en endurance fondamentale ?")
    
    # Si volume élevé
    if km_semaine >= 40:
        personalized.append("Comment maintenir ce volume sans me blesser ?")
    
    # Si peu de séances
    if 0 < nb_seances < 3:
        personalized.append("Comment optimiser avec peu de séances par semaine ?")
    
    # Si allure connue
    if allure and allure != "N/A":
        personalized.append(f"Comment améliorer mon allure de {allure}/km ?")
    
    # Compléter avec des suggestions de base (randomisées)
    remaining_needed = num_suggestions - len(personalized)
    if remaining_needed > 0:
        # Filtrer les suggestions déjà ajoutées
        available = [s for s in base_suggestions if s not in personalized]
        random.shuffle(available)
        personalized.extend(available[:remaining_needed])
    
    # Limiter à num_suggestions et mélanger
    result = personalized[:num_suggestions]
    random.shuffle(result)
    
    return result


def generate_response_with_suggestions(message: str, context: Dict, category: str = None) -> Dict:
    """
    Génère une réponse complète avec suggestions.
    Retourne un dictionnaire avec 'response' et 'suggestions'.
    NOTE: Plus de relance - les suggestions remplacent les relances du coach.
    """
    # D'abord, vérifier si c'est une réponse courte (réponse à une question précédente)
    message_lower = message.lower().strip()
    
    # Vérifier les réponses courtes connues
    for key, response_data in SHORT_RESPONSES.items():
        if message_lower == key or message_lower.startswith(key + " ") or message_lower.endswith(" " + key):
            # Pour les réponses courtes, utiliser des suggestions générales
            suggestions = get_personalized_suggestions("general", context, num_suggestions=random.randint(3, 4))
            return {
                "response": response_data["response"],  # Plus de relance
                "suggestions": suggestions,
                "category": "short_response"
            }
    
    # Si le message est très court (< 15 caractères) et pas reconnu
    if len(message_lower) < 15 and not any(kw in message_lower for cat in TEMPLATES.values() for kw in cat.get("keywords", [])):
        short_responses = [
            f"J'ai pas bien compris \"{message}\" 🤔 Tu peux me donner plus de détails ?",
            f"Hmm, \"{message}\"... tu veux dire quoi exactement ?",
            f"Je suis pas sûr de comprendre. Tu parles de ton entraînement ?",
            f"Peux-tu préciser un peu ? Je suis là pour t'aider sur la course ! 🏃",
        ]
        suggestions = get_personalized_suggestions("fallback", context, num_suggestions=random.randint(3, 5))
        return {
            "response": random.choice(short_responses),
            "suggestions": suggestions,
            "category": "unclear"
        }
    
    # Détection d'intention si pas de catégorie fournie
    if not category:
        category, confidence = detect_intent(message)
    
    # Générer la réponse principale (SANS relance)
    response_text = generate_response(message, context, category)
    
    # Générer les suggestions personnalisées (3 à 5)
    num_suggestions = random.randint(3, 5)
    suggestions = get_personalized_suggestions(category, context, num_suggestions)
    
    return {
        "response": response_text,
        "suggestions": suggestions,
        "category": category
    }


# ============================================================
# INTERFACE PRINCIPALE
# ============================================================

async def generate_chat_response(
    message: str,
    user_id: str,
    workouts: List[Dict] = None,
    user_goal: Dict = None,
    chat_history: List[Dict] = None
) -> Dict:
    """
    Fonction principale pour générer une réponse de chat avec suggestions.
    100% Python, pas de LLM, rapide (<1s)
    Retourne un dict avec 'response', 'suggestions', 'category', 'rag_chunks'
    
    RAG Sources:
    1. User workouts (get_user_training_context)
    2. Knowledge base tips (get_relevant_knowledge)
    3. Similar workouts comparison (context)
    """
    # RAG Source 1: Extraire le contexte d'entraînement (runs récents/historiques)
    context = get_user_training_context(workouts or [], user_goal)
    
    # Ajouter le nom de l'objectif au contexte si disponible
    if user_goal:
        context["objectif_nom"] = user_goal.get("event_name", "")
    
    # Détecter l'intention
    category, confidence = detect_intent(message)
    
    # RAG Source 2: Récupérer les connaissances pertinentes de la base statique
    knowledge_tips = get_relevant_knowledge(category, context)
    
    # Ajouter les tips au contexte pour les templates
    context["rag_tips"] = knowledge_tips
    context["rag_tip_1"] = knowledge_tips[0] if len(knowledge_tips) > 0 else ""
    context["rag_tip_2"] = knowledge_tips[1] if len(knowledge_tips) > 1 else ""
    context["rag_tip_3"] = knowledge_tips[2] if len(knowledge_tips) > 2 else ""
    
    # Générer la réponse avec suggestions (intègre les tips RAG)
    result = generate_response_with_suggestions(message, context, category)
    
    # Ajouter les chunks RAG utilisés pour traçabilité
    result["rag_chunks"] = knowledge_tips
    result["rag_sources"] = {
        "workouts_count": len(workouts or []),
        "knowledge_tips": len(knowledge_tips),
        "context_keys": list(context.keys())
    }
    
    return result


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def get_remaining_messages(tier: str, messages_used: int) -> int:
    """Calcule les messages restants selon le palier"""
    limits = {
        "free": 10,
        "starter": 25,
        "confort": 50,
        "pro": 999999  # Illimité
    }
    limit = limits.get(tier, 10)
    return max(0, limit - messages_used)


def check_message_limit(tier: str, messages_used: int) -> Tuple[bool, int]:
    """Vérifie si l'utilisateur peut encore envoyer des messages"""
    remaining = get_remaining_messages(tier, messages_used)
    can_send = remaining > 0
    return can_send, remaining
