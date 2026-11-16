"""
Vigie Urbaine - autoroutes A1 / A4 : geometrie reelle via Overpass (ref tag)
Chaine les troncons contigus et garde la plus longue chaine dans le bbox.
"""

import math
import sys
import time
from collections import defaultdict

import requests

BBOX = "36.65,10.03,36.98,10.46"
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


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


def contract(match, ways_nodes):
    """Chaine les troncons en match par extremites communes (5m)."""
    def key(p):
        return (round(p[0], 5), round(p[1], 5))

    start = {key(n[0]) for n in ways_nodes}
    end = {key(n[-1]) for n in ways_nodes}
    conn_start = start & end  # ways reliables
    used = [False] * len(ways_nodes)
    chains = []
    for i, nodes in enumerate(ways_nodes):
        if used[i]:
            continue
        chain = list(nodes)
        used[i] = True
        changed = True
        while changed:
            changed = False
            head = key(chain[0])
            tail = key(chain[-1])
            for j, cand in enumerate(ways_nodes):
                if used[j]:
                    continue
                ck_head, ck_tail = key(cand[0]), key(cand[-1])
                if ck_head == tail:
                    chain.extend(cand)
                    used[j] = True
                    changed = True
                    tail = key(chain[-1])
                elif ck_tail == head:
                    chain[:0] = list(reversed(cand))
                    used[j] = True
                    changed = True
                    head = key(chain[0])
        chains.append(chain)
    return max(chains, key=path_km)


def fetch(ref):
    q = f'[out:json][timeout:120];(way["highway"]["ref"~"^{ref}$"]({BBOX}););out geom;'
    last = None
    for url in MIRRORS:
        try:
            r = requests.post(
                url, data={"data": q}, timeout=180,
                headers={"User-Agent": "UrbanButterfly/1.0 (academic simulation)"},
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            print(f"  {url} : {exc}")
            last = exc
        time.sleep(10)
    raise RuntimeError(last)


def simplify(pts, max_points=60):
    dedup = []
    for p in pts:
        q = [round(p[0], 5), round(p[1], 5)]
        if not dedup or dedup[-1] != q:
            dedup.append(q)
    if len(dedup) <= max_points:
        return dedup
    step = math.ceil(len(dedup) / max_points)
    out = dedup[::step]
    if dedup[-1] != out[-1]:
        out.append(dedup[-1])
    return out


def main():
    lines = []
    for rid, ref in [("R1", "A1"), ("R4", "A4")]:
        data = fetch(ref)
        ways = [e for e in data.get("elements", []) if e.get("type") == "way" and e.get("geometry")]
        wn_list = [[(g["lat"], g["lon"]) for g in w["geometry"]] for w in ways]
        wn_list = [n for n in wn_list if len(n) > 1]
        chain = contract(ref, wn_list)
        flat = simplify(chain)
        lines.append(
            f"MATCH (r:Road:Infrastructure {{id:'{rid}'}}) SET r.path = [{', '.join(str(v) for v in [c for p in flat for c in p])}];"
        )
        print(f"{rid}: {ref} -> {len(flat)} pts, {path_km(chain):.1f} km chaines")

    with open("data/osm_paths_v6.cypher", "a", encoding="utf-8") as fh:
        fh.write("// autoroutes via Overpass tag ref=A1/A4\n")
        fh.write("\n".join(lines) + "\n")
    with open("data/seed.cypher", "a", encoding="utf-8") as fh:
        fh.write("// autoroutes A1/A4 via Overpass (tag ref, idempotent)\n")
        fh.write("\n".join(lines) + "\n")
    print("ecriture osm_paths_v6.cypher OK")


if __name__ == "__main__":
    sys.exit(main())
