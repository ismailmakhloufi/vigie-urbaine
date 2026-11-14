"""
Urban Butterfly - Events Router v1.1

Améliorations principales :
- mémorise le statut précédent de l'infrastructure avant modification ;
- restaure exactement ce statut lors de la résolution ;
- conserve le mécanisme last_event pour éviter qu'un ancien incident
  ne restaure un statut alors qu'un incident plus récent est actif ;
- ajoute explicitement status="ACTIVE" dans MongoDB ;
- conserve le stockage hybride MongoDB + Neo4j ;
- recalcule l'impact après création de l'événement.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.models.event import EventCreate
from app.models.impact import ImpactSummary
from app.services.cascade import compute_impact
from app.services.recommendations import build_recommendations


router = APIRouter(prefix="/events", tags=["Events"])


STATUS_BY_EVENT_TYPE = {
    "POWER_FAILURE": "OFFLINE",
    "CYBER_ATTACK": "COMPROMISED",
    "ROAD_BLOCKED": "BLOCKED",
    # HEAVY_RAIN cible une zone : on ne force pas son statut ici.
}


@router.post("", status_code=201)
def create_event(event: EventCreate):
    """
    Crée un événement réel.

    Étapes :
    1. Vérifie que la cible existe dans Neo4j.
    2. Sauvegarde son statut actuel.
    3. Insère l'événement dans MongoDB.
    4. Met à jour le statut de la cible si nécessaire.
    5. Crée le nœud Event dans Neo4j.
    6. Crée (Event)-[:AFFECTS]->(Infrastructure).
    7. Calcule immédiatement l'impact.
    """

    target = neo4j_client.query(
        """
        MATCH (t:Infrastructure {id: $target_id})
        RETURN
            t.id AS id,
            t.kind AS kind,
            t.name AS name,
            t.status AS status
        """,
        {"target_id": event.target_id},
    )

    if not target:
        raise HTTPException(
            404,
            f"target '{event.target_id}' not found in the graph",
        )

    target_data = target[0]

    # Document complet stocké dans MongoDB
    doc = event.model_dump()
    doc["timestamp"] = datetime.now(timezone.utc)
    doc["status"] = "ACTIVE"
    doc["previous_status"] = target_data.get("status")

    mongo_result = mongo_client.insert_event(doc)
    event_id = str(mongo_result.inserted_id)

    # Mise à jour éventuelle de l'état courant de l'infrastructure.
    new_status = STATUS_BY_EVENT_TYPE.get(event.type)

    if new_status:
        neo4j_client.query(
            """
            MATCH (t:Infrastructure {id: $target_id})
            SET
                t.status = $status,
                t.last_event = $event_id
            """,
            {
                "target_id": event.target_id,
                "status": new_status,
                "event_id": event_id,
            },
        )

    # Représentation de l'événement dans Neo4j
    neo4j_client.query(
        """
        CREATE (
            e:Event {
                id: $event_id,
                type: $type,
                severity: $severity,
                timestamp: $ts
            }
        )
        WITH e
        MATCH (t:Infrastructure {id: $target_id})
        MERGE (e)-[:AFFECTS]->(t)
        """,
        {
            "event_id": event_id,
            "type": event.type,
            "severity": event.severity,
            "ts": doc["timestamp"].isoformat(),
            "target_id": event.target_id,
        },
    )

    impact = compute_impact(event_id)

    return {
        "id": event_id,
        "status": "ACTIVE",
        "stored_in": ["mongodb", "neo4j"],
        "target": {
            "id": target_data["id"],
            "kind": target_data.get("kind"),
            "name": target_data.get("name"),
            "previous_status": target_data.get("status"),
            "current_status": new_status or target_data.get("status"),
        },
        "impact": impact,
    }


@router.get("")
def list_events(limit: int = 50):
    """
    Retourne les événements les plus récents.
    """
    return mongo_client.list_events(limit)


@router.get("/{event_id}/impact", response_model=ImpactSummary)
def event_impact(event_id: str):
    """
    Recalcule l'impact d'un événement existant.
    """
    try:
        return compute_impact(event_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.get("/{event_id}/recommendations")
def event_recommendations(event_id: str):
    """
    Plan d'action opérationnel pour un incident actif :
    contacts, actions, itineraires alternatifs optimaux et
    infrastructures de secours (antenne / poste)."""
    try:
        return build_recommendations(event_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/{event_id}/resolve")
def resolve_event(event_id: str):
    """
    Résout un événement.

    Le statut précédent enregistré dans MongoDB est restauré uniquement si :
    - l'événement existe ;
    - il est encore actif ;
    - il est toujours le dernier événement ayant modifié cette infrastructure.

    Cela évite qu'un ancien incident remette une infrastructure en état normal
    alors qu'un événement plus récent l'affecte encore.
    """

    event = mongo_client.get_event(event_id)

    if not event:
        raise HTTPException(
            404,
            f"event '{event_id}' not found in MongoDB",
        )

    if event.get("status") == "RESOLVED":
        return {
            "id": event_id,
            "status": "RESOLVED",
            "message": "event already resolved",
        }

    # Ces deux lectures sont informatives : une indisponibilité du moteur de
    # risque ne doit jamais empêcher la résolution réelle de l'incident.
    from app.routes.risk import risk_overview
    try:
        risk_before = risk_overview()
    except Exception as exc:
        print(f"[risk] historique avant résolution indisponible : {exc}")
        risk_before = None

    previous_status = event.get("previous_status")
    restored = False

    if previous_status is not None:
        result = neo4j_client.query(
            """
            MATCH (t:Infrastructure {id: $target_id})
            WHERE t.last_event = $event_id
            SET t.status = $previous_status
            REMOVE t.last_event
            RETURN
                t.id AS id,
                t.status AS status
            """,
            {
                "target_id": event["target_id"],
                "event_id": event_id,
                "previous_status": previous_status,
            },
        )

        restored = bool(result)

    mongo_client.set_event_status(event_id, "RESOLVED")

    if risk_before is not None:
        try:
            risk_after = risk_overview()
            before_nodes = {n["id"]: n for n in risk_before["nodes_at_risk"]}
            after_nodes = {n["id"]: n for n in risk_after["nodes_at_risk"]}
            changed = [
                {"id": ident, "name": n["name"], "before": n["score"],
                 "after": after_nodes.get(ident, {}).get("score", 0)}
                for ident, n in before_nodes.items()
                if n["score"] != after_nodes.get(ident, {}).get("score", 0)
            ]
            changed.sort(key=lambda n: (-(n["before"] - n["after"]), n["id"]))
            mongo_client.record_risk_transition({
                "event_id": event_id,
                "event_type": event["type"],
                "target_id": event["target_id"],
                "recorded_at": datetime.now(timezone.utc),
                "before_incidents": risk_before["active_incidents"],
                "after_incidents": risk_after["active_incidents"],
                "before_high": risk_before["counts_by_class"]["HIGH"] + risk_before["counts_by_class"]["CRITICAL"],
                "after_high": risk_after["counts_by_class"]["HIGH"] + risk_after["counts_by_class"]["CRITICAL"],
                "changed_count": len(changed),
                "top_changes": changed[:5],
            })
        except Exception as exc:
            print(f"[risk] historique après résolution indisponible : {exc}")

    return {
        "id": event_id,
        "status": "RESOLVED",
        "target_id": event.get("target_id"),
        "previous_status": previous_status,
        "restored": restored,
    }
