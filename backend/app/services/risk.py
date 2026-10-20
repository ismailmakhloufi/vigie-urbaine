"""
Urban Butterfly - Risk Engine v1.1

Objectif :
- calculer un score de risque explicable ;
- appliquer certaines règles générales à toutes les infrastructures ;
- appliquer les règles "backup électrique" uniquement aux types concernés ;
- retourner les raisons détaillées pour le frontend et la soutenance.

Score actuel :
- dépendance directe : +30
- dépendance indirecte : +10
- infrastructure critique (criticality >= 4) : +25
- absence de secours électrique : +20
  uniquement pour Hospital et TelecomTower
- plusieurs incidents actifs simultanés (>= 2) : +15
- sévérité HIGH : +5
- sévérité CRITICAL : +10

Classes :
- LOW      < 30
- MEDIUM   30-49
- HIGH     50-69
- CRITICAL >= 70
"""

POINT_DIRECT = 30
POINT_INDIRECT = 10
POINT_CRITICAL_INFRA = 25
POINT_NO_BACKUP = 20
POINT_MULTIPLE_INCIDENTS = 15
POINT_SEVERITY_CRITICAL = 10

SEVERITY_POINTS = {
    "LOW": 0,
    "MEDIUM": 0,
    "HIGH": 5,
    "CRITICAL": POINT_SEVERITY_CRITICAL,
}

# Types pour lesquels l'absence de secours électrique est réellement pertinente.
BACKUP_RELEVANT_KINDS = {
    "Hospital",
    "TelecomTower",
}


def risk_class(score: int) -> str:
    """Convertit un score numérique en classe de risque."""
    if score >= 70:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def score_node(
    kind: str,
    depth: int,
    criticality: int,
    backup_power_hours: int | float | None,
    severity: str,
    active_incidents: int,
) -> tuple[int, list[str]]:
    """
    Calcule le score de risque d'une infrastructure.

    Parameters
    ----------
    kind:
        Type d'infrastructure : Hospital, TelecomTower, Road, Warehouse, etc.
    depth:
        Profondeur de propagation depuis l'incident.
        1 = impact direct, >=2 = impact indirect.
    criticality:
        Niveau de criticité de l'infrastructure.
    backup_power_hours:
        Heures d'autonomie électrique de secours.
        None signifie "non applicable / inconnue".
    severity:
        LOW / MEDIUM / HIGH / CRITICAL.
    active_incidents:
        Nombre d'incidents actuellement actifs dans la ville.

    Returns
    -------
    tuple[int, list[str]]
        Score plafonné à 100 + raisons explicables.
    """
    reasons: list[str] = []
    score = 0

    # 1. Distance par rapport à l'incident
    if depth <= 1:
        score += POINT_DIRECT
        reasons.append(f"dépendance directe (+{POINT_DIRECT})")
    else:
        score += POINT_INDIRECT
        reasons.append(
            f"dépendance indirecte profondeur {depth} (+{POINT_INDIRECT})"
        )

    # 2. Criticité métier / infrastructurelle
    if criticality >= 4:
        score += POINT_CRITICAL_INFRA
        reasons.append(
            f"infrastructure critique (+{POINT_CRITICAL_INFRA})"
        )

    # 3. Backup électrique uniquement pour les types concernés
    if kind in BACKUP_RELEVANT_KINDS:
        if backup_power_hours is None or backup_power_hours <= 0:
            score += POINT_NO_BACKUP
            reasons.append(
                f"absence de secours électrique (+{POINT_NO_BACKUP})"
            )
        else:
            reasons.append(
                f"secours électrique disponible ({backup_power_hours} h)"
            )

    # 4. Contexte multi-incidents
    if active_incidents >= 2:
        score += POINT_MULTIPLE_INCIDENTS
        reasons.append(
            f"{active_incidents} incidents simultanés (+{POINT_MULTIPLE_INCIDENTS})"
        )

    # 5. Sévérité de l'événement
    severity_points = SEVERITY_POINTS.get(severity, 0)
    if severity_points:
        score += severity_points
        reasons.append(
            f"sévérité {severity} (+{severity_points})"
        )

    return min(score, 100), reasons

