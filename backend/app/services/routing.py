"""
Vigie Urbaine - Routing Engine v1.0

Dijkstra sur le reseau routier CONNECTS_TO avec cout dynamique :

    cout(edge) = travel_time_min
               + penalite trafic (par profil)
               + penalite risque inondation (flood_susceptibility)
               + penalite meteo ACTIVE (zones sous HEAVY_RAIN)
    route BLOCKED (ou cible d'un ROAD_BLOCKED actif) = exclu.

Profils :
    NORMAL    : equilibre
    AMBULANCE : vitesse + securite (penalise fort flood + trafic eleve)
    SUPPLY    : charge lourde, evite le trafic dense, tolere un peu de flood
"""

import heapq
import json
import math
from time import monotonic
from datetime import datetime, timezone
from pathlib import Path

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client

ACCESS_OVERHEAD_MIN = 2  # chargement/déchargement aux 2 extrémités

# L'audit du graphe (docs/audit-graphe.md) relève 6,68 km entre les
# tracés de R22 et R5 pour 1,4 km déclaré. Écarter la liaison dans les
# deux sens tant que sa géométrie et ses coûts n'ont pas été vérifiés.
_UNVERIFIED_ROAD_LINKS = {frozenset(("R22", "R5"))}
_OSM_ROAD_LINKS = json.loads(Path(__file__).with_name("osm_road_links.json").read_text(encoding="utf-8-sig"))


def road_link_is_usable(source: str, destination: str) -> bool:
    return frozenset((source, destination)) not in _UNVERIFIED_ROAD_LINKS


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(a))

PROFILE_WEIGHTS = {
    #              trafic,  flood,   rain,  time_mult
    "NORMAL": (2.0, 3.0, 4.0, 1.00),
    "AMBULANCE": (1.0, 8.0, 6.0, 0.80),
    "SUPPLY": (4.0, 5.0, 5.0, 1.10),
}


def _active_dynamic_state():
    """
    Lit les incidents actifs dans MongoDB :
    - ROAD_BLOCKED  -> routes a exclure ;
    - HEAVY_RAIN    -> zones sous alerte (routes penalisees).
    Retourne (blocked_ids : set, rainy_zone_ids : set, notes : list[str])
    """
    blocked = set()
    rainy_zones = set()
    notes = []
    docs = mongo_client._db.events.find(
        {"status": {"$ne": "RESOLVED"}},
        {"_id": 0, "type": 1, "target_id": 1},
    )
    for doc in docs:
        etype = doc.get("type")
        target = doc.get("target_id")
        if etype == "ROAD_BLOCKED":
            blocked.add(target)
            notes.append(f"ROAD_BLOCKED actif : {target} exclu(e).")
        elif etype == "HEAVY_RAIN":
            rainy_zones.add(target)
            notes.append(f"HEAVY_RAIN actif sur {target} : penalite inondation.")
    return blocked, rainy_zones, notes


# ----- cache reseau : la structure (routes + aretes) ne bouge presque jamais,
# on evite de requeter Neo4j a chaque itineraire. TTL court pour laisser
# passer les changements de statut (blocages). -----
_RESEAU_CACHE: dict = {"t": 0.0, "valeur": None}
_RESEAU_TTL = 10.0  # secondes


def _reseau() -> tuple[dict, list]:
    maintenant = monotonic()
    if _RESEAU_CACHE["valeur"] is None or maintenant - _RESEAU_CACHE["t"] > _RESEAU_TTL:
        _RESEAU_CACHE["valeur"] = _load_network()
        _RESEAU_CACHE["t"] = maintenant
    return _RESEAU_CACHE["valeur"]


def _load_network():
    """
    Charge noeuds (Road) + aretes (CONNECTS_TO) via Neo4j :
    retourne dict road_id -> {status, flood, name, zone}, et liste d'edges.
    """
    road_rows = neo4j_client.query(
        """
        MATCH (r:Road)
        OPTIONAL MATCH (r)-[:LOCATED_IN]->(z:Zone)
        RETURN r.id AS id, r.name AS name, r.status AS status,
               r.flood_susceptibility AS flood, z.id AS zone_id, z.name AS zone_name,
               r.path AS path
        """
    )
    roads = {
        row["id"]: {
            "name": row["name"],
            "status": row["status"] or "CLEAR",
            "flood": row["flood"] or 2,
            "zone_id": row["zone_id"],
            "zone_name": row["zone_name"],
        }
        for row in road_rows
    }

    edge_rows = neo4j_client.query(
        "MATCH (a:Road)-[e:CONNECTS_TO]->(b:Road) "
        "RETURN a.id AS src, b.id AS dst, e.distance_km AS km, "
        "e.travel_time_min AS minutes, e.traffic_level AS traffic, "
        "e.flood_susceptibility AS flood"
    )
    points = {
        row["id"]: list(zip(path[::2], path[1::2]))
        for row in road_rows if (path := row.get("path")) and len(path) >= 4
    }
    for edge in edge_rows:
        source, destination = edge["src"], edge["dst"]
        left, right = points.get(source, []), points.get(destination, [])
        osm = _OSM_ROAD_LINKS.get(f"{source}-{destination}")
        if osm:
            anchors = [tuple(reversed(list(map(float, anchor.split(","))))) for anchor in osm["anchors"]]
            if anchors[0] in left and anchors[1] in right:
                edge.update(km=osm["distance_km"], minutes=osm["minutes"], osm_path=osm["path"], uncertain=False)
                continue
        gap = min((_haversine(*a, *b) for a in left for b in right), default=None)
        declared_km = edge["km"]
        edge["uncertain"] = gap is None or gap > min(1.0, declared_km + 0.1)
        if gap is not None and gap > declared_km + 0.1:
            # Borne géographique pour les arcs simulés, en conservant leur vitesse implicite.
            minutes_per_km = edge["minutes"] / declared_km if edge["minutes"] and declared_km > 0 else 2.0
            edge.update(km=gap, minutes=gap * minutes_per_km)
    return roads, edge_rows


def _edge_cost(
    edge,
    profile: str,
    blocked: set,
    rainy_zones: set,
    roads: dict,
    mode: str = "FAST",
    corridor: bool = False,
    congestion: dict | None = None,
) -> float | None:
    dest = edge["dst"]

    d_road = roads.get(dest)
    if d_road is None:
        return None
    if dest in blocked or d_road["status"] == "BLOCKED":
        return None

    traffic_w, flood_w, rain_w, time_mult = PROFILE_WEIGHTS[profile]

    if mode == "SHORT":
        # le plus court en distance : on ignore trafic/inond/pluie
        return float(edge["km"]) * 1.8

    traffic_w *= 2.5 if mode == "SAFE" else 1.0
    flood_w *= 2.0 if mode == "SAFE" else 1.0

    cost = float(edge["minutes"] or edge["km"] * 2.0) * time_mult
    cost += (edge["traffic"] or 1) * traffic_w

    # trafic vivant : la congestion qui nait des incidents d'aujourd'hui
    if congestion:
        cost += congestion.get(dest, 0) * traffic_w
    if congestion and corridor:
        # corridor prioritaire : le gyrophare brise la file
        cost -= congestion.get(dest, 0) * traffic_w

    flood_level = d_road["flood"]
    if mode == "SAFE" and flood_level >= 3:
        # le mode SUR refuse par principe les rues a risque meme sans pluie
        cost += flood_w * (flood_level - 2)
    if rainy_zones and flood_level >= 3:
        cost += flood_w * (flood_level - 3)
    if rainy_zones and d_road["zone_id"] in rainy_zones:
        cost += rain_w
    if rainy_zones and flood_level >= 4 and d_road["zone_id"] in rainy_zones:
        cost += rain_w
    return cost


def _access_road(infra_id: str, blocked: set) -> tuple[str | None, float]:
    """
    Route d'acces d'une infrastructure :
    - si l'infra EST une route : elle-meme, cout 0 ;
    - sinon la route CLEAR de sa zone la plus proche (haversine),
      majoration de temps = distance / vitesse urbaine (25 km/h).
    Retourne (road_id, minutes_d_acces).
    """
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure {id: $id}) "
        "OPTIONAL MATCH (n)-[:LOCATED_IN]->(z:Zone) "
        "RETURN n.kind AS kind, n.status AS status, n.lat AS lat, n.lon AS lon, "
        "z.id AS zone_id LIMIT 1",
        {"id": infra_id},
    )
    if not rows:
        raise LookupError(f"infrastructure '{infra_id}' introuvable")

    row = rows[0]
    if row["kind"] == "Road":
        if infra_id in blocked or row["status"] == "BLOCKED":
            return None, 0.0
        return infra_id, 0.0

    if not row["zone_id"] or row["zone_id"] in blocked or row["lat"] is None or row["lon"] is None:
        return None, 0.0

    zone_roads = neo4j_client.query(
        "MATCH (r:Road)-[:LOCATED_IN]->(z:Zone {id: $zid}) "
        "WHERE (r.status = 'CLEAR' OR r.status IS NULL) "
        "RETURN r.id AS id, r.lat AS lat, r.lon AS lon",
        {"zid": row["zone_id"]},
    )

    best_id, best_min = None, math.inf
    for cand in zone_roads:
        if cand["lat"] is None or cand["lon"] is None or cand["id"] in blocked:
            continue
        minutes = _haversine(row["lat"], row["lon"], cand["lat"], cand["lon"]) / 25.0 * 60.0
        if minutes < best_min:
            best_min, best_id = minutes, cand["id"]
    if best_id is None:
        return None, 0.0
    return best_id, round(max(best_min, 1.0), 1)


def compute_route(
    origin_id: str,
    destination_id: str,
    profile: str = "AMBULANCE",
    mode: str = "FAST",
    corridor: bool = False,
    extra_blocked: set[str] | None = None,
) -> dict:
    roads, edges = _reseau()
    blocked, rainy_zones, notes = _active_dynamic_state()
    blocked = blocked | (extra_blocked or set())

    for rid, meta in roads.items():
        if meta["status"] == "BLOCKED":
            blocked.add(rid)

    # trafic vivant (phase "embouteillage qui nait du chaos")
    from app.services.traffic import congestion_map

    congestion = congestion_map()
    if mode in ("FAST", "SAFE"):
        congested = [rid for rid, bump in congestion.items() if bump >= 2]
        if congested:
            from app.services.traffic import describe
            notes.append(
                f"trafic vivant pris en compte : "
                + ", ".join(f"{rid} ({describe(congestion[rid])})" for rid in congested[:5])
            )

    origin_kind_rows = neo4j_client.query(
        "MATCH (n:Infrastructure {id: $id}) RETURN n.name AS name, n.kind AS kind",
        {"id": origin_id},
    )
    dest_rows = neo4j_client.query(
        "MATCH (n:Infrastructure {id: $id}) RETURN n.name AS name, n.kind AS kind",
        {"id": destination_id},
    )
    if not origin_kind_rows:
        raise LookupError(f"origin '{origin_id}' introuvable dans le graphe")
    if not dest_rows:
        raise LookupError(f"destination '{destination_id}' introuvable dans le graphe")

    # Acces geography-aware
    start_road, start_access_min = _access_road(origin_id, blocked)
    end_road, end_access_min = _access_road(destination_id, blocked)

    if not start_road:
        raise RuntimeError(f"Aucune route d'acces epargnee pour l'origine {origin_id}")
    if not end_road:
        raise RuntimeError(f"Aucune route d'acces epargnee pour la destination {destination_id}")

    # --- Dijkstra multi-source ---
    adj: dict[str, list[tuple[str, dict, float]]] = {}
    for edge in edges:
        src, dst = edge["src"], edge["dst"]
        if src == dst or src in blocked or dst in blocked:
            continue
        if not road_link_is_usable(src, dst):
            continue
        if roads.get(src, {}).get("status") == "BLOCKED":
            continue
        if roads.get(dst, {}).get("status") == "BLOCKED":
            continue
        cost = _edge_cost(edge, profile, blocked, rainy_zones, roads, mode=mode, corridor=corridor, congestion=congestion)
        if cost is None:
            continue
        adj.setdefault(src, []).append((dst, edge, cost))

    INFINITY = math.inf
    dist: dict[str, float] = {rid: INFINITY for rid in roads}
    prev_edge: dict[str, tuple[str, dict] | None] = {}
    heap: list[tuple[float, str]] = []

    for src in [start_road]:
        if src not in roads:
            continue
        dist[src] = 0.0
        heapq.heappush(heap, (0.0, src))

    visited: set[str] = set()
    while heap:
        d, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        if d > dist.get(node, INFINITY):
            continue
        for (nxt, edge, cost) in adj.get(node, []):
            nd = d + cost
            if nd < dist.get(nxt, INFINITY):
                dist[nxt] = nd
                prev_edge[nxt] = (node, edge)
                heapq.heappush(heap, (nd, nxt))

    best_end, best_cost = None, INFINITY
    for cid in [end_road]:
        if cid in dist and dist[cid] < best_cost:
            best_cost = dist[cid]
            best_end = cid

    if best_end is None or best_cost == INFINITY:
        raise RuntimeError(
            "Aucun itineraire disponible avec l'etat actuel de la ville "
            "(routes bloquees ou isolees)."
        )

    # reconstruction
    chain: list[str] = []
    segments_kms: list[float] = []
    segments_minutes: list[float] = []
    route_edges: list[dict] = []
    node = best_end
    while node is not None:
        chain.append(node)
        back = prev_edge.get(node)
        if back:
            prev_node, edge = back
            route_edges.append(edge)
            segments_kms.append(edge["km"])
            segments_minutes.append(float(edge["minutes"] or edge["km"] * 2.0))
            node = prev_node
        else:
            node = None
    chain.reverse()
    segments_kms.reverse()
    route_edges.reverse()

    total_kms = sum(segments_kms)
    # SHORT optimise les kilomètres : son coût Dijkstra n'est pas une durée.
    # L'ETA de cette variante reste une estimation des temps d'arêtes déclarés.
    route_time = sum(segments_minutes) * PROFILE_WEIGHTS[profile][3] if mode == "SHORT" else best_cost
    est_time = int(round(route_time + start_access_min + end_access_min))

    avoided: list[dict] = []
    for rid in sorted(blocked):
        meta = roads.get(rid)
        avoided.append({"id": rid, "reason": "BLOCKED"})
        if meta:
            avoided[-1]["name"] = meta["name"]
    flood_avoided = [
        {"id": rid, "reason": "FLOOD", "name": meta["name"]}
        for rid, meta in roads.items()
        if meta["flood"] >= 4
        and (meta["zone_id"] in rainy_zones)
        and rid not in chain
    ]
    avoided.extend(flood_avoided[:5])

    # polyligne GPS complete (chemins plats concatènes, doublons de jonction omis)
    path_rows = neo4j_client.query(
        "MATCH (r:Road) WHERE r.id IN $ids AND r.path IS NOT NULL "
        "RETURN r.id AS id, r.path AS path",
        {"ids": chain},
    )
    path_by_id = {row["id"]: row["path"] for row in path_rows}
    uncertain_links = []
    for edge in route_edges:
        if edge.get("uncertain", True):
            uncertain_links.append([edge["src"], edge["dst"]])
    full_path: list[float] = []
    road_offsets: list[dict] = []  # position cumulee (km) de chaque route du chain
    cum_km = 0.0
    all_osm = bool(route_edges) and all(edge.get("osm_path") for edge in route_edges)
    if all_osm:
        route_paths = [(edge["src"], edge["osm_path"]) for edge in route_edges]
        route_paths.append((chain[-1], route_edges[-1]["osm_path"][-2:]))
    else:
        route_paths = [(rid, path_by_id.get(rid)) for rid in chain]
    for rid, segment in route_paths:
        if not segment:
            continue
        start = cum_km
        pts = [(segment[i], segment[i + 1]) for i in range(0, len(segment) - 1, 2)]
        for j in range(1, len(pts)):
            cum_km += _haversine(pts[j - 1][0], pts[j - 1][1], pts[j][0], pts[j][1])
        if full_path[-2:] == segment[:2]:
            full_path.extend(segment[2:])
        else:
            full_path.extend(segment)
        road_offsets.append({"id": rid, "start_km": round(start, 3), "end_km": round(cum_km, 3)})

    if not full_path:
        road_offsets = []

    return {
        "origin_id": origin_id,
        "origin_name": origin_kind_rows[0]["name"],
        "destination_id": destination_id,
        "destination_name": dest_rows[0]["name"],
        "profile": profile,
        "route": chain,
        "route_names": [roads[r]["name"] for r in chain],
        "estimated_time_min": est_time,
        "distance_km": round(total_kms, 1),
        "uncertain_links": uncertain_links,
        "geometry_source": "OPENSTREETMAP_OSRM" if all_osm else "SIMULATION_GRAPH",
        "avoided": avoided[:8],
        "dynamic_notes": notes,
        "path": full_path,
        "road_offsets": road_offsets,
        "mode": mode,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


VARIANTS = [("FAST", "Rapide"), ("SHORT", "Court"), ("SAFE", "Sûr")]


def compute_route_options(origin_id: str, destination_id: str, profile: str = "AMBULANCE") -> dict:
    """Le comparateur du commandement : 3 propositions côte à côte."""
    options = []
    for mode, label in VARIANTS:
        try:
            route = compute_route(origin_id, destination_id, profile, mode=mode)
        except (LookupError, RuntimeError):
            continue
        options.append({
            "variant": mode,
            "label": label,
            "estimated_time_min": route["estimated_time_min"],
            "distance_km": route["distance_km"],
            "uncertain_links": route.get("uncertain_links", []),
            "geometry_source": route.get("geometry_source", "SIMULATION_GRAPH"),
            "route": route["route"],
            "route_names": route["route_names"],
            "path": route.get("path", []),
        })
    return {
        "origin_id": origin_id,
        "destination_id": destination_id,
        "profile": profile,
        "options": options,
    }
