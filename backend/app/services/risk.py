"""
Risk scoring engine (cahier des charges, section 13).

Score = sommes de points de regles explicites, plafonne a 100.
Regles :
  +30 dependance directe (profondeur 1) / +10 indirecte (profondeur >= 2)
  +25 infrastructure critique (criticality >= 4)
  +20 absence de secours (backup_power_hours == 0)
  +15 plusieurs incidents actifs simultanes (>= 2)
  +10 severite de l'evenement CRITICAL

Classes : LOW < 30 | MEDIUM 30-49 | HIGH 50-69 | CRITICAL >= 70
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


def risk_class(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def score_node(
    depth: int,
    criticality: int,
    backup_power_hours: int,
    severity: str,
    active_incidents: int,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0

    if depth <= 1:
        score += POINT_DIRECT
        reasons.append(f"dependance directe (+{POINT_DIRECT})")
    else:
        score += POINT_INDIRECT
        reasons.append(f"dependance indirecte profondeur {depth} (+{POINT_INDIRECT})")

    if criticality >= 4:
        score += POINT_CRITICAL_INFRA
        reasons.append(f"infrastructure critique (+{POINT_CRITICAL_INFRA})")

    if backup_power_hours == 0:
        score += POINT_NO_BACKUP
        reasons.append(f"absence de secours (+{POINT_NO_BACKUP})")

    if active_incidents >= 2:
        score += POINT_MULTIPLE_INCIDENTS
        reasons.append(f"{active_incidents} incidents simultanes (+{POINT_MULTIPLE_INCIDENTS})")

    sev_points = SEVERITY_POINTS.get(severity, 0)
    if sev_points:
        score += sev_points
        reasons.append(f"severite {severity} (+{sev_points})")

    return min(score, 100), reasons
