"""
Vigie Urbaine - SysOps Recommendation Engine v1.0

À partir d'un événement actif, le moteur produit un plan d'action :
- Gardes/ressources à contacter (contacts).
- Actions d'urgence classees (actions).
- Detours routiers calculés dans le graphe (itineraires detournes
  évitant toute route BLOCKED, l'ordre le plus court d'abord).
- Alternatives de secours (antenne telecom / poste électrique de repli
  dans la même zone ou la plus proche capa disponible).
"""

from app.db.neo4j_client import neo4j_client
from app.services.cascade import compute_impact


CONTACTS_BY_TYPE = {
    "ROAD_BLOCKED": [
        "SAMU 01 (ambulances BLS/ALS)",
        "STT Logistique (transporteurs médicaux)",
        "Protection Civile Tunis",
        "Direction Circulation - Grand Tunis",
        "Stations Taxis / VTC (renfort)",
    ],
    "POWER_FAILURE": [
        "STEG - Dispatch régional",
        "Maintenance électrotechnique (éclaireurs)",
        "Responsable maintenance infrastructures",
        "Gardes hôpitaux (chef d'exploitation / Damien)",
    ],
    "CYBER_ATTACK": [
        "CERT.tn (cellule Cyber)",
        "Opérateur télécom tier-1 (hotline 24/7)",
        "Référent DATA/digital santé",
        "Certification sécurité (chef d'équipe)",
    ],
    "HEAVY_RAIN": [
        "Garde Nationale (secours routiers)",
        "ONS / Travaux drainage",
        "Département météo (renouveler la vigilance)",
        "Protection Civile",
    ],
}

ACTIONS_BY_TYPE = {
    "ROAD_BLOCKED": [
        "Redirection immédiate des ambulances vers le corridor alternatif",
        "Signaler le blocage (Panneau mobile + RDS alerte)",
        "Rapprocher les livraisons médicales depuis les dépôts de remplacement",
    ],
    "POWER_FAILURE": [
        "Passer sur générateurs si autonomie <= 1 h",
        "Charge-élingage / délestement vers le poste de secours",
        "Prioriser la garde urgences + chaîne du froid",
    ],
    "CYBER_ATTACK": [
        "Isoler le point d'entrée compromis (segmentation réseau)",
        "Basculer les services sur l'antenne de repli",
        "Réinitialiser les sessions et audits d'identité",
    ],
    "HEAVY_RAIN": [
        "Dévier le trafic vers les axes non inondables",
        "Relever les niveaux d'eau et activer les pompes",
        "Suspendre les sorties scolaires/chantiers en zone",
    ],
}


def _coords_from_paths(road_ids):
    """Applatit les traces GPS de routes en une polyligne continue."""
    coords = []
    for rid in road_ids:
        rows = neo4j_client.query(
            "MATCH (r:Road {id: $rid}) RETURN r.path AS path",
            {"rid": rid},
        )
        if rows and rows[0].get("path"):
            flat = rows[0]["path"]
            for i in range(0, len(flat) - 1, 2):
                coords.append([flat[i], flat[i + 1]])
    # dedup points consécutifs identiques
    dedup = []
    for pt in coords:
        if not dedup or dedup[-1] != pt:
            dedup.append(pt)
    return dedup


def _compute_detours(event_type, target_id, impacts):
    """
    Construit jusqu'à 3 itineraires alternatifs :
    pied = roadway CLEAR adjacente à la route bloquée,
    tete = route au plus proche de la zone de chaque victime critique.
    """
    if event_type != "ROAD_BLOCKED":
        return []

    origin_rows = neo4j_client.query(
        """
        MATCH (r0:Road {id: $target_id})-[:LOCATED_IN]->(z0:Zone)
        MATCH (o:Road)-[:LOCATED_IN]->(z0)
        WHERE o.id <> $target_id AND (o.status = 'CLEAR' OR o.status IS NULL)
        RETURN collect(DISTINCT o.id) AS origins
        """,
        {"target_id": target_id},
    )
    origins = (origin_rows[0].get("origins") if origin_rows else None) or []
    if not origins:
        return []

    detours = []
    victims = sorted(
        (impact for impact in impacts if impact.kind in ("Hospital", "Pharmacy", "Warehouse")),
        key=lambda v: (-v.score, v.depth),
    )[:3]

    for victim in victims:
        zone_rows = neo4j_client.query(
            """
            MATCH (v:Infrastructure {id: $vid})-[:LOCATED_IN]->(z:Zone)
            MATCH (d:Road)-[:LOCATED_IN]->(z)
            WHERE d.status = 'CLEAR' OR d.status IS NULL
            RETURN collect(DISTINCT d.id) AS dests
            """,
            {"vid": victim.id},
        )
        dests = (zone_rows[0].get("dests") if zone_rows else None) or []
        if not dests:
            continue

        path_rows = neo4j_client.query(
            """
            MATCH p = (o:Road)-[:CONNECTED_BY*1..6]-(d:Road)
            WHERE o.id IN $origins AND d.id IN $dests
              AND o <> d
              AND all(x IN nodes(p) WHERE x.status = 'CLEAR' OR x.status IS NULL)
              AND none(x IN nodes(p) WHERE x.id = $target_id)
            WITH DISTINCT nodes(p) AS seg, length(p) AS jumps
            ORDER BY jumps
            LIMIT 1
            RETURN
                [x IN seg | x.id] AS ids,
                [x IN seg | x.name] AS names,
                jumps
            """,
            {"origins": origins, "dests": dests, "target_id": target_id},
        )
        if not path_rows:
            continue

        row = path_rows[0]
        detours.append(
            {
                "dest_id": victim.id,
                "dest_name": victim.name,
                "via_ids": row.get("ids") or [],
                "via_names": row.get("names") or [],
                "jumps": row.get("jumps"),
                "coords": _coords_from_paths(row.get("ids") or []),
            }
        )
    return detours


def _telecom_fallbacks(target_id):
    """Antennes ONLINE de repli, même zone si possible, sinon la plus proche."""
    same_zone = neo4j_client.query(
        """
        MATCH (t:TelecomTower {id: $target_id})-[:LOCATED_IN]->(z:Zone)
        MATCH (alt:TelecomTower)-[:LOCATED_IN]->(z)
        WHERE alt.id <> $target_id AND alt.status = 'ONLINE'
        RETURN alt.id AS id, alt.name AS name, alt.backup_power_hours AS backup
        ORDER BY backup DESC LIMIT 2
        """,
        {"target_id": target_id},
    )
    if same_zone:
        return[
            {
                "id": row["id"],
                "name": row["name"],
                "note": f"antenne de repli ({row['backup']} h de secours)",
            }
            for row in same_zone
        ]
    nearby = neo4j_client.query(
        """
        MATCH (t:TelecomTower {id: $target_id}), (alt:TelecomTower)
        WHERE alt.id <> $target_id AND alt.status = 'ONLINE'
        WITH t, alt,
            6371.0 * 2 * asin(sqrt(
                pow(sin(radians(alt.lat - t.lat) / 2), 2) +
                cos(radians(t.lat)) * cos(radians(alt.lat)) *
                pow(sin(radians(alt.lon - t.lon) / 2), 2)
            )) AS km
        RETURN alt.id AS id, alt.name AS name, km
        ORDER BY km ASC LIMIT 2
        """,
        {"target_id": target_id},
    )
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "note": f"antenne la plus proche ({round(row['km'], 1)} km)",
        }
        for row in nearby
    ]


def _power_fallbacks(target_id):
    """Postes ONLINE de repli (même zone puis capacité la plus élevée)."""
    same_zone = neo4j_client.query(
        """
        MATCH (p:PowerStation {id: $target_id})-[:LOCATED_IN]->(z:Zone)
        MATCH (alt:PowerStation)-[:LOCATED_IN]->(z)
        WHERE alt.id <> $target_id AND alt.status = 'ONLINE'
        RETURN alt.id AS id, alt.name AS name, alt.capacity_mw AS capacity
        ORDER BY capacity DESC LIMIT 2
        """,
        {"target_id": target_id},
    )
    if same_zone:
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "note": f"poste de repli ({row['capacity']} MW)",
            }
            for row in same_zone
        ]
    alts = neo4j_client.query(
        """
        MATCH (p:PowerStation {id: $target_id}), (alt:PowerStation)
        WHERE alt.id <> $target_id AND alt.status = 'ONLINE'
        RETURN alt.id AS id, alt.name AS name,
               alt.capacity_mw AS capacity
        ORDER BY capacity DESC LIMIT 2
        """,
        {"target_id": target_id},
    )
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "note": f"poste dispo ({row['capacity']} MW)",
        }
        for row in alts
    ]


def build_recommendations(event_id: str) -> dict:
    event_rows = neo4j_client.query(
        """
        MATCH (e:Event {id: $event_id})-[:AFFECTS]->(t:Infrastructure)
        RETURN e.type AS type, e.severity AS severity,
               t.id AS target_id, t.name AS target_name
        """,
        {"event_id": event_id},
    )
    if not event_rows:
        raise LookupError(f"event '{event_id}' has no AFFECTS link in the graph")

    head = event_rows[0]
    event_type = head["type"]
    target_id = head["target_id"]
    impact = compute_impact(event_id)

    detours = _compute_detours(event_type, target_id, impact.impacts)

    alternatives = []
    if target_id.startswith("T") and event_type in ("CYBER_ATTACK", "POWER_FAILURE"):
        alternatives = _telecom_fallbacks(target_id)
    elif target_id.startswith("P") and event_type == "POWER_FAILURE":
        alternatives = _power_fallbacks(target_id)

    return {
        "event_id": event_id,
        "type": event_type,
        "severity": head["severity"],
        "target_id": target_id,
        "target_name": head["target_name"],
        "contacts": CONTACTS_BY_TYPE.get(event_type, []),
        "actions": ACTIONS_BY_TYPE.get(event_type, []),
        "detours": detours,
        "alternatives": alternatives,
        "impacted_total": impact.total_count,
        "max_depth": impact.max_depth,
    }
