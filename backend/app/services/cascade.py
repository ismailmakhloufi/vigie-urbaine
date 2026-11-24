"""
Vigie Urbaine - Cascade Engine v1.1

Rôle :
- calculer la propagation d'un événement dans le graphe Neo4j ;
- distinguer les scénarios POWER_FAILURE / CYBER_ATTACK,
  ROAD_BLOCKED et HEAVY_RAIN ;
- exploiter DEPENDS_ON, CONNECTED_BY, LOCATED_IN et SUPPLIED_BY ;
- dédupliquer les infrastructures touchées en conservant la profondeur minimale ;
- calculer le score de risque de chaque nœud impacté.

Important :
Cette version suppose que app.services.risk.score_node(...) accepte
le paramètre `kind` :

    score_node(
        kind: str,
        depth: int,
        criticality: int,
        backup_power_hours: int | None,
        severity: str,
        active_incidents: int,
    )

Le mode What-if tient compte des incidents actuellement actifs afin de simuler
"que se passerait-il si cet incident arrivait maintenant ?".
"""

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.models.impact import ImpactNode, ImpactSummary
from app.services.risk import risk_class, score_node


MAX_PROPAGATION_DEPTH = 5
MAX_ROAD_ACCESS_DISTANCE_M = 5000  # tolérance large pour les points de référence des rues


def _active_incidents() -> int:
    """Retourne le nombre d'incidents non résolus actuellement actifs."""
    return mongo_client.count_active_events()


def _propagation_rows(event_type: str, target_id: str) -> list[dict]:
    """
    Retourne les infrastructures potentiellement impactées par un événement.

    Chaque ligne doit contenir :
    - id
    - kind
    - name
    - depth
    - criticality
    - backup_power_hours

    Règles :
    - POWER_FAILURE / CYBER_ATTACK :
        propagation via DEPENDS_ON.
    - ROAD_BLOCKED :
        accès direct via CONNECTED_BY, sans propagation à travers tout le
        réseau routier ; approvisionnement seulement si l'entrepôt n'a pas
        d'autre accès routier disponible.
    - HEAVY_RAIN :
        la cible est une Zone.
        exposition estimée des infrastructures LOCATED_IN la zone ;
        aucune propagation inter-zones par route sans preuve d'inondation.
    """

    if event_type == "ROAD_BLOCKED":
        return neo4j_client.query(
            f"""
            MATCH (r:Road:Infrastructure {{id: $target_id}})

            CALL (r) {{

                MATCH (x:Infrastructure)-[:CONNECTED_BY]->(r)
                WHERE (x:Road OR (
                    x.lat IS NOT NULL AND x.lon IS NOT NULL
                    AND r.lat IS NOT NULL AND r.lon IS NOT NULL
                    AND point.distance(point({{latitude: x.lat, longitude: x.lon}}),
                                       point({{latitude: r.lat, longitude: r.lon}})) <= $max_access_distance_m
                )) AND (x:Road OR NOT EXISTS {{
                    MATCH (x)-[:CONNECTED_BY]->(alternative:Road)
                    WHERE alternative <> r AND coalesce(alternative.status, 'CLEAR') <> 'BLOCKED'
                }})

                RETURN
                    x.id AS id,
                    x.kind AS kind,
                    x.name AS name,
                    1 AS depth,
                    x.criticality AS criticality,
                    x.backup_power_hours AS backup_power_hours,
                    [{{id: r.id, name: r.name, kind: r.kind}},
                     {{id: x.id, name: x.name, kind: x.kind}}] AS chain

                UNION

                MATCH (warehouse:Warehouse:Infrastructure)-[:CONNECTED_BY]->(r)
                WHERE warehouse.lat IS NOT NULL AND warehouse.lon IS NOT NULL
                  AND r.lat IS NOT NULL AND r.lon IS NOT NULL
                  AND point.distance(point({{latitude: warehouse.lat, longitude: warehouse.lon}}),
                                     point({{latitude: r.lat, longitude: r.lon}})) <= $max_access_distance_m
                  AND NOT EXISTS {{
                    MATCH (warehouse)-[:CONNECTED_BY]->(alternative:Road)
                    WHERE alternative <> r AND coalesce(alternative.status, 'CLEAR') <> 'BLOCKED'
                }}
                MATCH (service:Infrastructure)-[:SUPPLIED_BY]->(warehouse)

                RETURN
                    service.id AS id,
                    service.kind AS kind,
                    service.name AS name,
                    2 AS depth,
                    service.criticality AS criticality,
                    service.backup_power_hours AS backup_power_hours,
                    [{{id: r.id, name: r.name, kind: r.kind}},
                     {{id: warehouse.id, name: warehouse.name, kind: warehouse.kind}},
                     {{id: service.id, name: service.name, kind: service.kind}}] AS chain
            }}

            RETURN DISTINCT
                id,
                kind,
                name,
                depth,
                criticality,
                backup_power_hours,
                chain
            """,
            {"target_id": target_id, "max_access_distance_m": MAX_ROAD_ACCESS_DISTANCE_M},
        )

    if event_type == "HEAVY_RAIN":
        return neo4j_client.query(
            """
            MATCH (z:Zone:Infrastructure {id: $target_id})
            MATCH (x:Infrastructure)-[:LOCATED_IN]->(z)
            WHERE NOT x:Zone
            RETURN x.id AS id, x.kind AS kind, x.name AS name,
                   1 AS depth, x.criticality AS criticality,
                   x.backup_power_hours AS backup_power_hours,
                   [{id: z.id, name: z.name, kind: z.kind},
                    {id: x.id, name: x.name, kind: x.kind}] AS chain
            """,
            {"target_id": target_id},
        )

    return neo4j_client.query(
        f"""
        MATCH p =
            (x:Infrastructure)-[:DEPENDS_ON*1..{MAX_PROPAGATION_DEPTH}]
            ->(t:Infrastructure {{id: $target_id}})

        RETURN
            x.id AS id,
            x.kind AS kind,
            x.name AS name,
            length(p) AS depth,
            x.criticality AS criticality,
            x.backup_power_hours AS backup_power_hours,
            [n IN reverse(nodes(p)) | {{id: n.id, name: n.name, kind: n.kind}}] AS chain
        """,
        {"target_id": target_id},
    )


def compute_impact(event_id: str, active_incidents: int | None = None) -> ImpactSummary:
    """
    Calcule l'impact d'un événement réellement enregistré.
    """
    head = neo4j_client.query(
        """
        MATCH (e:Event {id: $event_id})-[:AFFECTS]->(t:Infrastructure)
        RETURN
            e.type AS type,
            e.severity AS severity,
            t.id AS target_id
        """,
        {"event_id": event_id},
    )

    if not head:
        raise LookupError(
            f"event '{event_id}' has no AFFECTS link in the graph"
        )

    event = head[0]

    return build_impact(
        event_type=event["type"],
        severity=event["severity"],
        target_id=event["target_id"],
        event_id=event_id,
        active_incidents=active_incidents,
    )


def compute_hypothetical(
    event_type: str,
    severity: str,
    target_id: str,
) -> ImpactSummary:
    """
    Mode What-if : aucun événement n'est créé et aucun statut n'est modifié.
    """
    return build_impact(
        event_type=event_type,
        severity=severity,
        target_id=target_id,
        event_id=None,
    )


def build_impact(
    event_type: str,
    severity: str,
    target_id: str,
    event_id: str | None,
    active_incidents: int | None = None,
) -> ImpactSummary:
    """
    Construit le résumé final d'impact :
    - propagation Neo4j ;
    - déduplication ;
    - profondeur minimale ;
    - scoring ;
    - classification du risque.
    """
    rows = _propagation_rows(event_type, target_id)
    if active_incidents is None:
        active_incidents = _active_incidents()

    best_rows: dict[str, dict] = {}

    for row in rows:
        node_id = row.get("id")
        depth = row.get("depth")

        if not node_id or depth is None:
            continue

        current = best_rows.get(node_id)

        if (current is None or depth < current["depth"] or
                (depth == current["depth"] and
                 [n["id"] for n in row.get("chain") or []] <
                 [n["id"] for n in current.get("chain") or []])):
            best_rows[node_id] = row

    impacts: list[ImpactNode] = []

    for row in best_rows.values():
        depth = int(row["depth"])
        kind = row.get("kind") or "Unknown"

        score, reasons = score_node(
            kind=kind,
            depth=depth,
            criticality=int(row.get("criticality") or 0),
            backup_power_hours=row.get("backup_power_hours"),
            severity=severity,
            active_incidents=active_incidents,
            event_type=event_type,
        )

        impacts.append(
            ImpactNode(
                id=row["id"],
                kind=kind,
                name=row.get("name") or row["id"],
                depth=depth,
                score=score,
                risk=risk_class(score),
                reasons=reasons,
                chain=row.get("chain") or [],
                criticality=int(row.get("criticality") or 0),
                backup_power_hours=row.get("backup_power_hours"),
            )
        )

    impacts.sort(key=lambda node: (node.depth, -node.score, node.id))

    return ImpactSummary(
        event_id=event_id or "WHAT-IF",
        event_type=event_type,
        severity=severity,
        target_id=target_id,
        impacts=impacts,
        direct_count=sum(1 for impact in impacts if impact.depth == 1),
        total_count=len(impacts),
        max_depth=max((impact.depth for impact in impacts), default=0),
    )
