"""
Urban Butterfly - Rafraichissement geometrie routiere depuis OpenStreetMap
(geocodage Nominatim - polygon_geojson)

Pour chacune des 30 routes :
    1. requete Nominatim "nom de route, Tunis" ( vraies geometries OSM )
    2. choix du meilleur candidat : type de voie > longueur > proximite de l'ancien
       point central
    3. simplification <= 60 points, ecriture du path plat : Neo4j + seed.cypher

Usage : backend/.venv/Scripts/python.exe scripts/refresh_osm_paths.py
"""

import math
import sys
import time
from urllib.parse import quote

import requests

API = "http://127.0.0.1:8000"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
VIEWBOX = "10.03,36.98,10.46,36.65"  # minX, maxY, maxX, minY (Grand Tunis)
MAX_POINTS = 60
NEAR_KM = 8.0
TYPE_RANK = {
    "trunk": 0, "motorway": 0, "primary": 1, "secondary": 2,
    "tertiary": 3, "unclassified": 4, "residential": 5, "service": 9,
}

# variantes de recherche par route ; la premiere qui matche bien gagne
SEARCH = {
    "R1": ["Autoroute A1 Tunisie"],
    "R2": ["Avenue Habib Bourguiba, Tunis"],
    "R3": ["Route Tenor, Tunis"],
    "R4": ["Autoroute A4, Tunis"],
    "R5": ["Boulevard de l'Environnement, Tunis", "Rocade Sud Est, Tunis"],
    "R6": ["Rue de Marseille, Tunis"],
    "R7": ["Avenue de la Liberté, Tunis"],
    "R8": ["Rue Bab Saadoun, Tunis"],
    "R9": ["Gammarth, La Marsa", "Route de Gammarth, Tunis"],
    "R10": ["Avenue Habib Bourguiba, La Marsa"],
    "R11": ["Rue Sidi Daoud, La Marsa", "Rue Sidi Dhrif, Tunis"],
    "R12": ["Rue de la République, Tunis", "Avenue de la République, Tunis"],
    "R13": ["Rue Ibn Khaldoun, Tunis"],
    "R14": ["Route de l'Ariana, Ariana", "Route Ariana Lac, Tunis", "Chemin de l'Ariana, Tunis"],
    "R15": ["Rue Hedi Nouira, Tunis"],
    "R16": ["Djellaz, Tunis", "Jellaz, Tunis"],
    "R17": ["Sidi Hassine, Tunis", "Route Sidi Hassine, Tunis"],
    "R18": ["Rue Ibn Sina, Tunis"],
    "R19": ["Route de l'Oued, Ben Arous", "Oued, Ben Arous"],
    "R20": ["Ariana, Tunis", "Avenue de l'Ariana, Tunis"],
    "R21": ["Rue de Belgique, Tunis", "Rue Belgique, Tunis"],
    "R22": ["Boulevard du Lac, Tunis"],
    "R23": ["Avenue Farhat Hached, Tunis"],
    "R24": ["Rue de la République, Ben Arous", "Centre ville, Ben Arous"],
    "R25": ["Avenue Mohamed V, Tunis"],
    "R26": ["Route de Marsa Plage", "Plage, La Marsa"],
    "R27": ["Rue du Lac Turkana, Tunis"],
    "R28": ["Mégrine, Tunis", "Zone industrielle, Ben Arous"],
    "R29": ["Rue Ibn Abi Dhiaf, Tunis"],
    "R30": ["Rue Hedi Cherif, Tunis", "Avenue Hedi Cherif, Tunis"],
}


def haversine_km(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def path_km(pts):
    return sum(haversine_km(*pts[i - 1], *pts[i]) for i in range(1, len(pts)))


def midpoint(pts):
    return pts[len(pts) // 2]


def to_points(geom):
    gtype = geom["type"]
    if gtype == "LineString":
        return [(pt[1], pt[0]) for pt in geom["coordinates"]]
    if gtype == "MultiLineString":
        pts = []
        for part in geom["coordinates"]:
            pts.extend((p[1], p[0]) for p in part)
        return pts
    return []


def simplify(pts):
    dedup = []
    for p in pts:
        q = [round(p[0], 5), round(p[1], 5)]
        if not dedup or dedup[-1] != q:
            dedup.append(q)
    if len(dedup) <= MAX_POINTS:
        return [c for p in dedup for c in p]
    step = math.ceil(len(dedup) / MAX_POINTS)
    out = dedup[::step]
    if dedup[-1] != out[-1]:
        out.append(dedup[-1])
    return [c for p in out for c in p]


def search(session, query):
    r = session.get(
        NOMINATIM,
        params={
            "q": query,
            "format": "geojson",
            "polygon_geojson": 1,
            "limit": 6,
            "countrycodes": "tn",
            "viewbox": VIEWBOX,
            "bounded": 1,
        },
        timeout=60,
    )
    r.raise_for_status()
    features = []
    for f in r.json().get("features", []):
        g = f.get("geometry") or {}
        pts = to_points(g)
        props = f.get("properties", {})
        features.append((pts, props.get("type", ""), props.get("display_name", "")))
    return features


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "UrbanButterfly/1.0 (academic simulation)"})
    infra = requests.get(f"{API}/infrastructure", timeout=30).json()
    roads = {n["id"]: n for n in infra if n["kind"] == "Road"}

    outputs = []
    for rid, variants in SEARCH.items():
        road = roads.get(rid)
        if road is None:
            continue
        old_path = road.get("path") or []
        ref = (
            midpoint([(old_path[i], old_path[i + 1]) for i in range(0, len(old_path) - 1, 2)])
            if len(old_path) >= 4 else (road.get("lat"), road.get("lon"))
        )

        best = None
        for variant in variants:
            try:
                cands = search(session, variant)
            except Exception as exc:
                print(f"{rid}: requete ratee ({variant}) : {exc}")
                time.sleep(1.5)
                continue
            time.sleep(1.2)
            for pts, wtype, display in cands:
                # Nominatim classe par pertinence : on garde le PREMIER candidat
                # de vraie route ddans le secteur, assez long pour etre realiste
                if len(pts) < 3 or wtype not in TYPE_RANK:
                    continue
                if path_km(pts) < 0.2:
                    continue
                if ref and haversine_km(*midpoint(pts), *ref) > NEAR_KM:
                    continue
                best = (path_km(pts), pts, wtype, display, variant)
                break
            if best:
                break

        if best is None:
            print(f"{rid}: AUCUN match OSM -> path neuf conserve")
            continue

        flat = simplify(best[1])
        name = best[3].split(",")[0]
        outputs.append(
            f"MATCH (r:Road:Infrastructure {{id:'{rid}'}}) SET r.path = [{', '.join(str(v) for v in flat)}];"
        )
        print(f"{rid}: [{best[2]}] {name} ({flat and path_km(best[1]):.1f} km, {len(flat)//2} pts) <- {best[4]}")

    if not outputs:
        print("Rien a ecrire")
        return

    with open("data/osm_paths_v6.cypher", "w", encoding="utf-8") as fh:
        fh.write("// v6 - chemins GPS reels OpenStreetMap via Nominatim (refresh_osm_paths.py)\n")
        fh.write("\n".join(outputs) + "\n")
    with open("data/seed.cypher", "a", encoding="utf-8") as fh:
        fh.write("\n// ===== v6 - CHEMINS GPS REELS OpenStreetMap / Nominatim (idempotent) =====\n")
        fh.write("\n".join(outputs) + "\n")
    print(f"\ndata/osm_paths_v6.cypher : {len(outputs)} routes")


if __name__ == "__main__":
    sys.exit(main())
