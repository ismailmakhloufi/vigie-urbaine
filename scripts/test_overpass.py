import requests

params = {
    "q": "Rue Bab Saadoun, Tunis",
    "format": "geojson",
    "polygon_geojson": 1,
    "limit": 5,
    "countrycodes": "tn",
    "viewbox": "10.03,36.98,10.46,36.65",  # minX, maxY, maxX, minY
    "bounded": 1,
}
r = requests.get(
    "https://nominatim.openstreetmap.org/search",
    params=params,
    headers={"User-Agent": "UrbanButterfly/1.0 (academic simulation)"},
    timeout=60,
)
print("status", r.status_code)
data = r.json()
for f in data.get("features", [])[:5]:
    g = f["geometry"]
    typ = f["properties"].get("type")
    name = f["properties"].get("display_name", "")[:70]
    npts = sum(len(part) for part in (g["coordinates"] if g["type"] != "Point" else [])) or 1
    print(f"- [{typ}] {name} | {g['type']} x{npts} pts")
