"""
Urban Butterfly - Cascade Engine v1.1

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
        impact direct via CONNECTED_BY + impact logistique via SUPPLIED_BY.
    - HEAVY_RAIN :
        la cible est une Zone.
        impact direct sur les infrastructures LOCATED_IN la zone
        + impact transport via les routes de la zone.
    """

    if event_type == "ROAD_BLOCKED":
        return neo4j_client.query(
            f"""
            MATCH (r:Road:Infrastructure {{id: $target_id}})

            CALL {{
                WITH r

                MATCH p = (x:Infrastructure)-[:CONNECTED_BY*1..{MAX_PROPAGATION_DEPTH}]->(r)

                RETURN
                    x.id AS id,
                    x.kind AS kind,
                    x.name AS name,
                    length(p) AS depth,
                    x.criticality AS criticality,
                    x.backup_power_hours AS backup_power_hours

                UNION

                WITH r

                MATCH (warehouse:Warehouse:Infrastructure)-[:CONNECTED_BY]->(r)
                MATCH (service:Infrastructure)-[:SUPPLIED_BY]->(warehouse)

                RETURN
                    service.id AS id,
                    service.kind AS kind,
                    service.name AS name,
                    2 AS depth,
                    service.criticality AS criticality,
                    service.backup_power_hours AS backup_power_hours
            }}

            RETURN DISTINCT
                id,
                kind,
                name,
                depth,
                criticality,
                backup_power_hours
            """,
            {"target_id": target_id},
        )

    if event_type == "HEAVY_RAIN":
        return neo4j_client.query(
            f"""
            MATCH (z:Zone:Infrastructure {{id: $target_id}})

            CALL {{
                WITH z

                MATCH (x:Infrastructure)-[:LOCATED_IN]->(z)
                WHERE NOT x:Zone

                RETURN
                    x.id AS id,
                    x.kind AS kind,
                    x.name AS name,
                    1 AS depth,
                    x.criticality AS criticality,
                    x.backup_power_hours AS backup_power_hours

                UNION

                WITH z

                MATCH (r:Road:Infrastructure)-[:LOCATED_IN]->(z)
                MATCH p = (x:Infrastructure)-[:CONNECTED_BY*1..{MAX_PROPAGATION_DEPTH}]->(r)
                WHERE x <> r

                RETURN
                    x.id AS id,
                    x.kind AS kind,
                    x.name AS name,
                    length(p) + 1 AS depth,
                    x.criticality AS criticality,
                    x.backup_power_hours AS backup_power_hours
            }}

            RETURN DISTINCT
                id,
                kind,
                name,
                depth,
                criticality,
                backup_power_hours
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
            x.backup_power_hours AS backup_power_hours
        """,
        {"target_id": target_id},
    )


def compute_impact(event_id: str) -> ImpactSummary:
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
    active_incidents = _active_incidents()

    best_rows: dict[str, dict] = {}

    for row in rows:
        node_id = row.get("id")
        depth = row.get("depth")

        if not node_id or depth is None:
            continue

        current = best_rows.get(node_id)

        if current is None or depth < current["depth"]:
            best_rows[node_id] = row

    impacts: list[ImpactNode] = []

    for row in best_rows.values():
        depth = int(row["depth"])
        kind = row.get("kind") or "Unknown"

        score, reasons = score_node(
            kind=kind,
            depth=min(depth, 2),
            criticality=int(row.get("criticality") or 0),
            backup_power_hours=row.get("backup_power_hours"),
            severity=severity,
            active_incidents=active_incidents,
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

