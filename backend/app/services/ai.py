"""
Urban Butterfly - AI Narrator v1.0 (etape 11)

Rôle du LLM : reformuler UNIQUEMENT des faits calculés par
le graphe + le moteur de risque. Aucun invent.

Flux :
1. La question de l'utilisateur est analysée (id/zone/motif).
2. On récupère les FAITS : nœuds concernés, risques, raisons,
   cascades actives, plan d'action.
3. On demande à Llama 3.1 (Ollama) une réponse courte en français
   à partir uniquement de ces faits.
"""

import json
import re

import requests

from app.core.config import get_settings
from app.db.neo4j_client import neo4j_client
from app.db.mongo_client import mongo_client
from app.services.cascade import compute_impact
from app.services.recommendations import build_recommendations
from app.services.risk import score_node


def _llm_chat(system: str, user: str, temperature: float = 0.2) -> str:
    """Appel non-streaming à Ollama. Lève RuntimeError si indisponible."""
    settings = get_settings()
    url = f"{settings.ollama_url}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        response = requests.post(url, json=payload, timeout=240)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"LLM indisponible : {exc}") from exc
    return response.json()["message"]["content"].strip()


SYSTEM_PROMPT = (
    "Tu es l'assistant IA d'Urban Butterfly, un simulateur de risques "
    "urbains en cascade qui surveille le Grand Tunis (jumeau numérique "
    "Neo4j + MongoDB). Règles absolues :\n"
    "1. Réponds en FRANÇAIS, concis (max 6 phrases), style cellule de crise.\n"
    "2. Utilise UNIQUEMENT les faits fournis entre <<<FAITS>>> ... <<<FIN>>>. "
    "N'invente aucun chiffre, aucun nœud, aucune relation.\n"
    "3. Si l'information manque dans les faits, dis-le clairement.\n"
    "4. Explique le pourquoi en s'appuyant sur les raisons de score fournies.\n"
    "5. Pas de markdown lourd : phrases courtes, puces simples autorisées."
)


def _facts_for_node(node_id: str) -> dict | None:
    """Assemble tous les faits connus concernant un nœud d'infrastructure."""
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure {id: $id}) "
        "OPTIONAL MATCH (n)-[:LOCATED_IN]->(z:Zone) "
        "RETURN n.id AS id, n.kind AS kind, n.name AS name, n.status AS status, "
        "n.criticality AS criticality, z.id AS zone_id, z.name AS zone_name",
        {"id": node_id},
    )
    if not rows:
        return None

    facts: dict = dict(rows[0])

    incident = mongo_client._db.events.find_one(
        {"target_id": node_id, "status": "ACTIVE"}, sort=[("timestamp", -1)]
    )
    if incident:
        event_id = str(incident["_id"])
        try:
            impact = compute_impact(event_id)
            facts["incident_actif"] = {
                "event_id": event_id,
                "type": incident.get("type"),
                "severity": incident.get("severity"),
                "description": incident.get("description", ""),
                "impacts": [
                    {
                        "id": n.id,
                        "nom": n.name,
                        "type": n.kind,
                        "profondeur": n.depth,
                        "score": n.score,
                        "risque": n.risk,
                        "raisons": n.reasons,
                    }
                    for n in impact.impacts[:10]
                ],
            }
        except LookupError:
            pass
    else:
        active_count = mongo_client.count_active_events()
        kind = facts.get("kind")
        severity = "CRITICAL" if kind in ("Hospital", "PowerStation") else "HIGH"
        score, reasons = score_node(
            kind=facts.get("kind") or "Unknown",
            depth=1,
            criticality=int(facts.get("criticality") or 0),
            backup_power_hours=None,
            severity="MEDIUM",
            active_incidents=active_count,
        )
        facts["aucun_incident_actif"] = True
        facts["contexte_generique"] = {
            "incidents_actifs_dans_la_ville": active_count,
            "score_si_evenement": score,
            "raisons_si_evenement": reasons,
        }
    return facts


def _extract_node_id(question: str) -> str | None:
    """Cherche un id concret (H1, R19, PH4...) dans la question."""
    match = re.search(r"\b([HPTWZRPh]\d{1,2}|PH\d{1,2})\b", question)
    if match:
        candidate = match.group(1).upper()
        exists = neo4j_client.query(
            "MATCH (n:Infrastructure {id: $id}) RETURN 1 AS ok LIMIT 1",
            {"id": candidate},
        )
        if exists:
            return candidate
        return None
    return None


def _find_by_name(question: str) -> str | None:
    candidates = neo4j_client.query(
        "MATCH (n:Infrastructure) "
        "WHERE toLower(n.name) CONTAINS toLower($q) "
        "RETURN n.id AS id LIMIT 1",
        {"q": question.strip()},
    )
    return candidates[0]["id"] if candidates else None


def answer_question(question: str) -> dict:
    """Chat IA explicatif principal."""
    node_id = _extract_node_id(question)

    if node_id is None and len(question.strip()) > 6:
        node_id = _find_by_name(question)

    facts_payload: dict = {"question": question}

    if node_id:
        facts = _facts_for_node(node_id)
        facts_payload["cible"] = facts
    else:
        city = neo4j_client.query(
            "MATCH (t:Infrastructure) WHERE t.status <> 'ONLINE' "
            "RETURN t.id AS id, t.kind AS kind, t.status AS status LIMIT 5"
        )
        active = mongo_client.count_active_events()
        facts_payload["ville"] = {
            "incidents_actifs": active,
            "infra_degradees": city,
        }
        if not city:
            facts_payload["ville"]["note"] = (
                "aucune infrastructure en statut dégradé ; la ville est stable."
            )

    facts_text = json.dumps(facts_payload, ensure_ascii=False, indent=1)
    prompt = (
        f"Question de l'opérateur : {question}\n\n"
        f"<<<FAITS>>>\n{facts_text}\n<<<FIN>>>"
    )
    try:
        content = _llm_chat(SYSTEM_PROMPT, prompt)
        mode = "llm"
    except RuntimeError as exc:
        fallback = _template_answer(facts_payload, str(exc))
        content, mode = fallback, "template"

    return {"answer": content, "mode": mode, "facts": facts_payload}


def _template_answer(facts: dict, err: str) -> str:
    """Réponses honnêtes mêmes sans LLM (fallback déterministe)."""
    cible = facts.get("cible")
    if cible:
        lines = [
            f"{cible.get('name')} ({cible.get('id')}) — "
            f"statut {cible.get('status')}, criticité {cible.get('criticality')}/5."
        ]
        inc = cible.get("incident_actif")
        if inc:
            lines.append(
                f"Incident {inc['type']} ({inc['severity']}) actif : "
                f"{len(inc['impacts'])} nœud(s) touchés."
            )
            for n in inc["impacts"][:3]:
                lines.append(f"- {n['nom']} ({n['id']}) : {n['score']}/100 {n['risque']}")
        else:
            lines.append("Aucun incident actif ne la touche actuellement.")
        lines.append(f"[mode résumé local — LLM indisponible : {err[:80]}]")
        return "\n".join(lines)
    ville = facts.get("ville", {})
    return (
        f"Ville : {ville.get('incidents_actifs', 0)} incident(s) actif(s). "
        f"Infrastructure(s) dégradée(s) : "
        f"{', '.join(x['id'] + '(' + x['status'] + ')' for x in ville.get('infra_degradees', [])) or 'aucune'}. "
        f"[mode résumé local — LLM indisponible : {err[:80]}]"
    )


def generate_briefing() -> dict:
    """Briefing de situation complet pour la cellule de crise."""
    active_events = list(
        mongo_client._db.events.find(
            {"status": {"$ne": "RESOLVED"}},
            {"_id": 1, "type": 1, "severity": 1, "target_id": 1},
        )
        .sort("timestamp", -1)
        .limit(4)
    )
    blocks = []

    degraded = neo4j_client.query(
        "MATCH (n:Infrastructure) WHERE n.status <> 'ONLINE' AND NOT n:Zone "
        "RETURN n.id AS id, n.kind AS kind, n.name AS name, n.status AS status "
        "ORDER BY n.kind, n.id",
    )

    if not degraded:
        city_state = neo4j_client.query(
            "MATCH (n:Infrastructure) RETURN count(n) AS total",
        )
        blocks.append(
            f"Aucune infrastructure dégradée ; la ville ({city_state[0]['total']} nœuds) "
            "est en état nominal."
        )
    else:
        for row in degraded[:8]:
            blocks.append(f"- {row['id']} {row['name']} [{row['status']}]")

    for ae in active_events[:4]:
        event_id = str(ae["_id"])
        try:
            impact = compute_impact(event_id)
            worst = max(impact.impacts, key=lambda n: n.score, default=None)
            line = (
                f"Incident {ae['type']} ({ae['severity']}) sur {ae['target_id']} : "
                f"{impact.total_count} impacts, profondeur {impact.max_depth}."
            )
            if worst:
                line += f" Pire victime : {worst.id} ({worst.score}/100 {worst.risk})."
            try:
                plan = build_recommendations(event_id)
                detours = plan.get("detours") or []
                alts = plan.get("alternatives") or []
                if detours:
                    line += f" Détours calculés : {', '.join(d['dest_id'] for d in detours)}."
                if alts:
                    line += f" Repli possible : {', '.join(a['id'] for a in alts)}."
            except LookupError:
                pass
            blocks.append(line)
        except LookupError:
            blocks.append(f"Incident {event_id} : cascade non recalculable.")

    if not blocks:
        return {"text": "Situation stable : aucun incident actif.", "mode": "template"}

    facts_text = "\n".join(blocks)
    prompt = (
        "Rédige un briefing de situation pour la cellule de crise du Grand Tunis "
        "(format : SITUATION / PRIORITÉS / ACTIONS) à partir uniquement des "
        "faits ci-dessous.\n\n"
        f"<<<FAITS>>>\n{facts_text}\n<<<FIN>>>"
    )
    try:
        content = _llm_chat(SYSTEM_PROMPT, prompt)
        mode = "llm"
    except RuntimeError:
        mode = "template"
        content = "BRIEFING (rédaction locale)\n\n" + "\n".join(facts_text.split("\n"))

    return {"text": content, "mode": mode}
