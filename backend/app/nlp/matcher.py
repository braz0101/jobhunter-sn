"""
Moteur de matching : compare une offre d'emploi avec le profil user.

Score final (0.0 → 1.0) = somme pondérée de 4 sous-scores :
  - skills   (45%) : overlap Jaccard entre compétences offre ↔ profil
  - title    (25%) : présence de rôles cibles dans le titre
  - location (20%) : Dakar > Sénégal > Remote > Afrique > Autre
  - contract (10%) : préférence de type de contrat
"""

from typing import TypedDict
from unidecode import unidecode
import re

from app.nlp.skill_extractor import extract_skills, extract_job_type, extract_location_type
from app.nlp.user_profile import USER_PROFILE
from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# TYPES
# ─────────────────────────────────────────────────────────────────────────────

class ScoreBreakdown(TypedDict):
    skills_score: float
    title_score: float
    location_score: float
    contract_score: float
    final_score: float


class MatchResult(TypedDict):
    matching_score: float
    score_breakdown: ScoreBreakdown
    skills_matched: list[str]
    skills_missing: list[str]
    skills_extracted: list[str]
    match_explanation: str
    job_type: str | None
    is_remote: bool


# ─────────────────────────────────────────────────────────────────────────────
# PRÉ-CALCUL DU PROFIL (fait une seule fois)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', unidecode(text).lower().strip())

_PROFILE_SKILLS: set[str] = set(USER_PROFILE["competences"])
_PROFILE_ROLES: list[str] = [_normalize(r) for r in USER_PROFILE["roles_cibles"]]
_PROFILE_LOCATIONS: list[str] = [_normalize(l) for l in USER_PROFILE["localisation_preferee"]]
_PROFILE_CONTRACTS: list[str] = [_normalize(t) for t in USER_PROFILE["types_contrat"]]


# ─────────────────────────────────────────────────────────────────────────────
# SOUS-SCORES
# ─────────────────────────────────────────────────────────────────────────────

def _score_skills(job_skills: list[str]) -> tuple[float, list[str], list[str]]:
    """
    Jaccard modifié : pénalise moins si l'offre demande peu de skills.

    Formule : |intersection| / (|union| * damping_factor)
    Le damping_factor atténue la pénalité quand l'offre est générique.
    """
    if not job_skills:
        return 0.0, [], []

    job_set = set(job_skills)
    matched = sorted(_PROFILE_SKILLS & job_set)
    missing = sorted(job_set - _PROFILE_SKILLS)

    if not matched:
        return 0.0, [], list(missing)

    # Jaccard standard
    union = len(_PROFILE_SKILLS | job_set)
    intersection = len(matched)
    jaccard = intersection / union

    # Boost si beaucoup de compétences matchées (reward pour forte compatibilité)
    coverage = intersection / len(job_set)          # % des skills demandés qu'on a
    profile_coverage = intersection / len(_PROFILE_SKILLS)  # % de notre profil utilisé

    # Score combiné : jaccard de base + bonus coverage
    score = 0.6 * jaccard + 0.2 * coverage + 0.2 * profile_coverage
    return round(min(score, 1.0), 4), matched, missing


def _score_title(title: str, description: str = "") -> float:
    """
    Cherche les rôles cibles du profil dans le titre (principalement) et description.
    Le titre compte double.
    """
    title_norm = _normalize(title)
    desc_norm = _normalize(description[:500] if description else "")
    combined = title_norm + " " + title_norm + " " + desc_norm  # titre en double

    best_score = 0.0
    for role in _PROFILE_ROLES:
        role_words = role.split()
        # Compte combien de mots du rôle sont présents
        hits = sum(1 for word in role_words if re.search(r'\b' + re.escape(word) + r'\b', combined))
        score = hits / len(role_words)
        if score > best_score:
            best_score = score
        if best_score >= 0.85:  # early exit
            break

    return round(best_score, 4)


def _score_location(location: str, is_remote: bool) -> float:
    """
    Hiérarchie de score géographique :
      Dakar         → 1.0
      Sénégal       → 0.85
      Remote        → 0.75
      Afrique franco → 0.55
      International  → 0.35
      Inconnu        → 0.50 (on ne pénalise pas ce qu'on ne sait pas)
    """
    if not location:
        return 0.50

    loc_norm = _normalize(location)

    if any(kw in loc_norm for kw in ["dakar"]):
        return 1.0
    if any(kw in loc_norm for kw in ["senegal", "sénégal", "saint-louis", "thies", "ziguinchor"]):
        return 0.85
    if is_remote or any(kw in loc_norm for kw in ["remote", "teletravail", "distance"]):
        return 0.75
    if any(kw in loc_norm for kw in ["abidjan", "cote d ivoire", "bamako", "mali", "douala",
                                      "cameroun", "dakar", "afrique", "africa", "mauritanie",
                                      "guinee", "maroc", "tunis", "algerie"]):
        return 0.55
    return 0.35


def _score_contract(job_type: str | None, is_remote: bool) -> float:
    """Score selon le type de contrat."""
    if job_type is None:
        return 0.50  # Neutre si non détecté
    job_type_norm = _normalize(job_type)
    if job_type_norm in _PROFILE_CONTRACTS:
        return 1.0
    # Types acceptables mais pas préférés
    if job_type_norm in ["freelance", "consulting"]:
        return 0.60
    return 0.20


# ─────────────────────────────────────────────────────────────────────────────
# MOTEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def match_job(
    title: str,
    description: str,
    location: str = "",
    job_type_hint: str | None = None,
) -> MatchResult:
    """
    Calcule le score de matching complet pour une offre.

    Args:
        title:          Titre de l'offre
        description:    Description complète
        location:       Localisation indiquée
        job_type_hint:  Type déjà extrait (optionnel, sinon extrait depuis description)

    Returns:
        MatchResult avec score, breakdown, skills matched/missing, explication
    """
    full_text = f"{title} {description}"

    # Extraction
    job_skills = extract_skills(full_text)
    job_type   = job_type_hint or extract_job_type(full_text)
    is_remote  = extract_location_type(full_text)

    # Sous-scores
    s_skills, matched, missing = _score_skills(job_skills)
    s_title    = _score_title(title, description)
    s_location = _score_location(location, is_remote)
    s_contract = _score_contract(job_type, is_remote)

    # Score final pondéré
    w = settings
    final = (
        w.WEIGHT_SKILLS   * s_skills +
        w.WEIGHT_TITLE    * s_title +
        w.WEIGHT_LOCATION * s_location +
        w.WEIGHT_CONTRACT * s_contract
    )
    final = round(min(final, 1.0), 4)

    breakdown = ScoreBreakdown(
        skills_score=round(s_skills, 4),
        title_score=round(s_title, 4),
        location_score=round(s_location, 4),
        contract_score=round(s_contract, 4),
        final_score=final,
    )

    explanation = _generate_explanation(
        final, matched, missing, s_title, s_location, job_type, is_remote
    )

    return MatchResult(
        matching_score=final,
        score_breakdown=dict(breakdown),
        skills_matched=matched,
        skills_missing=missing,
        skills_extracted=job_skills,
        match_explanation=explanation,
        job_type=job_type,
        is_remote=is_remote,
    )


def _generate_explanation(
    score: float,
    matched: list[str],
    missing: list[str],
    title_score: float,
    location_score: float,
    job_type: str | None,
    is_remote: bool,
) -> str:
    """Génère une explication lisible du score."""
    parts = []

    # Niveau global
    if score >= 0.80:
        parts.append("✅ Excellente compatibilité")
    elif score >= 0.60:
        parts.append("🟡 Bonne compatibilité")
    elif score >= 0.40:
        parts.append("🟠 Compatibilité partielle")
    else:
        parts.append("🔴 Faible compatibilité")

    # Compétences
    if matched:
        top = matched[:5]
        parts.append(f"Compétences matchées : {', '.join(top)}" + (" ..." if len(matched) > 5 else ""))
    if missing:
        top_miss = missing[:3]
        parts.append(f"Compétences à acquérir : {', '.join(top_miss)}")

    # Titre
    if title_score >= 0.8:
        parts.append("Titre très aligné avec ton profil")
    elif title_score < 0.3:
        parts.append("Titre peu aligné avec tes rôles cibles")

    # Localisation
    if location_score == 1.0:
        parts.append("📍 Dakar")
    elif location_score >= 0.85:
        parts.append("📍 Sénégal")
    elif is_remote:
        parts.append("🌐 Remote")

    # Type
    if job_type:
        parts.append(f"Type : {job_type.upper()}")

    return " | ".join(parts)
