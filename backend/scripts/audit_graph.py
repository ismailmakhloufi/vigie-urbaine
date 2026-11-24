"""Audit géographique en lecture seule du graphe Neo4j chargé.

Depuis backend : .venv/Scripts/python scripts/audit_graph.py > audit.md
Distances = minimum entre points des tracés, pas distance routière ni preuve
de jonction. Aucun incident, aucune arête ni aucun statut n'est modifié.
"""

import math
import sys
from collections import defaultdict, deque
from pathlib import Path

from neo4j import GraphDatabase, READ_ACCESS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings


def km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(h)))


def points(road):
    path = road.get("path") or []
    if len(path) >= 2 and len(path) % 2 == 0:
        return list(zip(path[::2], path[1::2]))
    if road.get("lat") is not None and road.get("lon") is not None:
        return [(road["lat"], road["lon"])]
    return []


def gap(left, right):
    a, b = points(left), points(right)
    return min((km(x, y) for x in a for y in b), default=None)


def components(graph, excluded_edge=None):
    # Aucune hypothèse de sens de circulation : mesure topologique seulement.
    seen, result = set(), []
    for node in graph:
        if node in seen:
            continue
        group, queue = {node}, deque([node])
        while queue:
            current = queue.popleft()
            for neighbor in graph[current]:
                if frozenset((current, neighbor)) == excluded_edge or neighbor in group:
                    continue
                group.add(neighbor)
                queue.append(neighbor)
        seen |= group
        result.append(group)
    return result


def audit(roads, route_edges, access_edges, threshold_km=1):
    by_id = {road["id"]: road for road in roads}
    graph = defaultdict(set, {ident: set() for ident in by_id})
    pairs = {}
    for edge in route_edges:
        a, b = edge["src"], edge["dst"]
        if a not in by_id or b not in by_id:
            continue
        pair = tuple(sorted((a, b)))
        pairs.setdefault(pair, edge)
        graph[a].add(b)
        graph[b].add(a)
    base = components(graph)
    print("# Audit du graphe routier chargé (lecture seule)\n")
    print(f"{len(by_id)} routes ; {len(pairs)} paires CONNECTS_TO ; {len(access_edges)} liens CONNECTED_BY site→route ; {len(base)} composante(s) routière(s).")
    print("Distances minimales à vol d'oiseau entre sommets des tracés ; un faible écart ne prouve **pas** une jonction (pont, sens, accès). Seuil de tri indicatif : 1 km.\n")
    print("## CONNECTS_TO à examiner (écart > 1 km ou métrique déclarée inférieure à l'écart)\n")
    print("| Lien | Écart tracés km | Coût déclaré km | Alerte | Sans ce lien |")
    print("|---|---:|---:|---|---|")
    flagged = []
    for (a, b), edge in pairs.items():
        distance = gap(by_id[a], by_id[b])
        stated = edge.get("km")
        flags = []
        if distance is None:
            flags.append("tracé manquant")
        elif distance > threshold_km:
            flags.append("écart important")
        if distance is not None and stated is not None and distance > stated + 0.1:
            flags.append("coût < distance directe")
        if flags:
            after = components(graph, frozenset((a, b)))
            consequence = f"{len(after)} composantes" if len(after) > len(base) else "détours possibles (non quantifiés)"
            flagged.append((distance if distance is not None else -1, a, b, stated, flags, consequence))
    for distance, a, b, stated, flags, consequence in sorted(flagged, reverse=True):
        print(f"| {a}–{b} | {distance:.2f} | {stated if stated is not None else '—'} | {', '.join(flags)} | {consequence} |")
    print(f"\n{len(flagged)} paire(s) signalée(s) sur {len(pairs)} ; les arêtes non listées ne sont pas pour autant validées.\n")
    print("## CONNECTED_BY site→route à examiner (> 1 km)\n")
    print("| Site | Route | Distance point→tracé km |")
    print("|---|---|---:|")
    suspect = []
    for edge in access_edges:
        road = by_id.get(edge["road_id"])
        site = edge["site"]
        if not road or site.get("lat") is None or site.get("lon") is None:
            suspect.append((-1, site["id"], edge["road_id"]))
            continue
        distance = min((km((site["lat"], site["lon"]), p) for p in points(road)), default=-1)
        if distance < 0 or distance > threshold_km:
            suspect.append((distance, site["id"], edge["road_id"]))
    for distance, site, road in sorted(suspect, reverse=True):
        print(f"| {site} | {road} | {distance:.2f} |")
    print(f"\n{len(suspect)} lien(s) signalé(s) sur {len(access_edges)}. Les points des sites et tracés ne constituent pas des adresses vérifiées.\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cfg = get_settings()
    with GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password)) as driver:
        with driver.session(default_access_mode=READ_ACCESS) as session:
            def read(tx):
                roads = [r.data() for r in tx.run("MATCH (r:Road) RETURN r.id AS id, r.lat AS lat, r.lon AS lon, r.path AS path")]
                edges = [r.data() for r in tx.run("MATCH (a:Road)-[e:CONNECTS_TO]->(b:Road) RETURN a.id AS src, b.id AS dst, e.distance_km AS km")]
                access = [r.data() for r in tx.run("MATCH (s:Infrastructure)-[:CONNECTED_BY]->(r:Road) WHERE NOT s:Road RETURN {id:s.id, lat:s.lat, lon:s.lon} AS site, r.id AS road_id")]
                return roads, edges, access
            audit(*session.execute_read(read))


if __name__ == "__main__":
    main()
