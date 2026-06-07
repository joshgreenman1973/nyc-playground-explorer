#!/usr/bin/env python3
"""
Build data for the NYC Playground & Court Explorer.

Outputs
  data/places.json         -- every playground + court, with real polygon shapes,
                              centroid, park id, and all available detail fields.
  data/neighborhoods.json  -- 2020 NTA polygons with playground counts + density.

Sources (NYC Open Data, Dept. of Parks & Recreation + City Planning):
  j55h-3upk  Playgrounds with Dedicated Children's Areas (DCAs)
  qnem-b8re  Athletic Facilities (per-sport flags)
  enfh-gkve  Parks Properties (park name + cross streets, joined on gispropnum)
  9nt8-h7nd  2020 Neighborhood Tabulation Areas (boundaries + area)
"""

import json
import urllib.request
import urllib.parse
from shapely.geometry import shape, Point, mapping
from shapely.strtree import STRtree

DCA_ID, ATH_ID, PROP_ID, NTA_ID = "j55h-3upk", "qnem-b8re", "enfh-gkve", "9nt8-h7nd"
BASE = "https://data.cityofnewyork.us/resource/{}.json"
SQFT_PER_SQMI = 27_878_400.0

BORO = {"M": "Manhattan", "B": "Brooklyn", "X": "Bronx",
        "Q": "Queens", "R": "Staten Island"}

COURT_SPORTS = [
    ("basketball", "Basketball"), ("handball", "Handball"),
    ("tennis", "Tennis"), ("pickleball", "Pickleball"),
    ("volleyball", "Volleyball"), ("bocce", "Bocce"),
]


def fetch(dataset_id, params):
    params = dict(params)
    params["$limit"] = 60000
    url = BASE.format(dataset_id) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "nyc-playground-explorer"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def rings_latlng(geom, prec=5):
    """Exterior rings as [[lat,lng],...] lists (one per polygon part). Compact."""
    if not geom:
        return None
    out = []
    coords = geom.get("coordinates", [])
    polys = coords if geom.get("type") == "MultiPolygon" else [coords]
    for poly in polys:
        if not poly:
            continue
        ring = [[round(y, prec), round(x, prec)] for x, y in poly[0]]
        if len(ring) >= 3:
            out.append(ring)
    return out or None


def round_geojson(geom, prec=5):
    """Recursively round all coordinates in a GeoJSON geometry dict."""
    def r(c):
        if isinstance(c, (int, float)):
            return round(c, prec)
        return [r(x) for x in c]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def centroid_of(rings):
    xs = [pt[1] for r in rings for pt in r]
    ys = [pt[0] for r in rings for pt in r]
    return [round(sum(ys) / len(ys), 6), round(sum(xs) / len(xs), 6)]


def build():
    places = []

    # --- Park name + cross-street lookup ---
    parks = {}
    for row in fetch(PROP_ID, {"$select": "gispropnum,signname,location,name311"}):
        gid = row.get("gispropnum")
        if gid:
            parks[gid] = {"name": (row.get("signname") or row.get("name311") or "").strip(),
                          "loc": (row.get("location") or "").strip()}

    # --- Playgrounds (children's play areas) ---
    for row in fetch(DCA_ID, {}):
        rings = rings_latlng(row.get("shape"))
        if not rings:
            continue
        places.append({
            "kind": "playground",
            "name": (row.get("publicname") or "Playground").strip(),
            "loc": (row.get("publiclocation") or "").strip(),
            "boro": BORO.get(row.get("borough", ""), row.get("borough", "")),
            "prop": row.get("gispropnum", ""),
            "sports": [], "acc": None, "surface": "", "dim": "",
            "c": centroid_of(rings), "poly": rings,
        })

    # --- Courts (active athletic facilities for our sports) ---
    where = ("featurestatus='Active' AND ("
             + " OR ".join(f"{k}=true" for k, _ in COURT_SPORTS) + ")")
    for row in fetch(ATH_ID, {"$where": where}):
        rings = rings_latlng(row.get("multipolygon"))
        if not rings:
            continue
        sports = [lab for key, lab in COURT_SPORTS if str(row.get(key)).lower() == "true"]
        if not sports:
            continue
        park = parks.get(row.get("gispropnum"), {})
        places.append({
            "kind": "court",
            "name": park.get("name") or (sports[0] + " courts"),
            "loc": park.get("loc", ""),
            "boro": BORO.get(row.get("borough", ""), row.get("borough", "")),
            "prop": row.get("gispropnum", ""),
            "sports": sports,
            "acc": str(row.get("accessible")).lower() == "true",
            "surface": (row.get("surface_type") or "").strip(),
            "dim": (row.get("dimensions") or "").strip(),
            "c": centroid_of(rings), "poly": rings,
        })

    with open("data/places.json", "w") as f:
        json.dump(places, f, separators=(",", ":"))

    # ---------- Neighborhood density (playgrounds per square mile) ----------
    nta_rows = fetch(NTA_ID, {})
    geoms, metas = [], []
    for row in nta_rows:
        g = row.get("the_geom")
        if not g:
            continue
        try:
            poly = shape(g)
        except Exception:
            continue
        geoms.append(poly)
        try:
            area_sqmi = float(row.get("shape_area", 0)) / SQFT_PER_SQMI
        except (TypeError, ValueError):
            area_sqmi = 0.0
        # simplify for the web (~15m tolerance) and round coordinates
        simplified = round_geojson(mapping(poly.simplify(0.00015, preserve_topology=True)))
        metas.append({
            "name": row.get("ntaname", ""),
            "boro": row.get("boroname", ""),
            "type": row.get("ntatype", ""),     # 0 = residential; non-0 = parks/cemeteries/etc
            "area": round(area_sqmi, 4),
            "count": 0,
            "geom_geojson": simplified,
        })

    tree = STRtree(geoms)
    pg_pts = [Point(p["c"][1], p["c"][0]) for p in places if p["kind"] == "playground"]
    for pt in pg_pts:
        for idx in tree.query(pt):
            if geoms[idx].contains(pt):
                metas[idx]["count"] += 1
                break

    features, ranking = [], []
    for m in metas:
        per_sqmi = round(m["count"] / m["area"], 2) if m["area"] > 0 else 0.0
        props = {"name": m["name"], "boro": m["boro"], "type": m["type"],
                 "count": m["count"], "area": m["area"], "per_sqmi": per_sqmi}
        features.append({"type": "Feature", "properties": props, "geometry": m["geom_geojson"]})
        # rank residential NTAs only (type "0") with non-trivial area
        if m["type"] == "0" and m["area"] >= 0.05:
            ranking.append(props)

    with open("data/neighborhoods.json", "w") as f:
        json.dump({"type": "FeatureCollection", "features": features},
                  f, separators=(",", ":"))

    # ---------- Report ----------
    pg = sum(1 for p in places if p["kind"] == "playground")
    ct = sum(1 for p in places if p["kind"] == "court")
    print(f"Playgrounds: {pg}   Courts: {ct}   Total: {len(places)}")
    matched = sum(m["count"] for m in metas)
    print(f"Playgrounds matched to a neighborhood: {matched}/{pg}")
    ranking.sort(key=lambda r: r["per_sqmi"], reverse=True)
    print("\nMost playground-dense neighborhoods (per sq mi):")
    for r in ranking[:12]:
        print(f"  {r['per_sqmi']:5.1f}  {r['name']} ({r['boro']}) — {r['count']} in {r['area']:.2f} sq mi")
    print("\nLeast dense residential neighborhoods with >=0.2 sq mi:")
    big = [r for r in ranking if r["area"] >= 0.2]
    big.sort(key=lambda r: r["per_sqmi"])
    for r in big[:10]:
        print(f"  {r['per_sqmi']:5.1f}  {r['name']} ({r['boro']}) — {r['count']} in {r['area']:.2f} sq mi")


if __name__ == "__main__":
    build()
