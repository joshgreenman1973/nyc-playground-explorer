#!/usr/bin/env python3
"""
Build the data bundle for the NYC Playground & Court Explorer.

Sources (NYC Open Data, Dept. of Parks & Recreation):
  - Playgrounds with Dedicated Children's Areas (DCAs): j55h-3upk
      Spaces with play equipment designed for children (play structures /
      climbers / slides / swings, plus spray showers). NYC Parks' own
      authoritative "where are the kid playgrounds" layer.
  - Athletic Facilities: qnem-b8re
      Every permitable / designated sports facility, with per-sport flags
      (basketball, handball, tennis, pickleball, volleyball, bocce, ...).

Output: data/places.json  -- one compact record per place.
"""

import json
import urllib.request
import urllib.parse

DCA_ID = "j55h-3upk"
ATH_ID = "qnem-b8re"
PROP_ID = "enfh-gkve"  # Parks Properties -> park name + cross streets by gispropnum
BASE = "https://data.cityofnewyork.us/resource/{}.json"

BORO = {"M": "Manhattan", "B": "Brooklyn", "X": "Bronx",
        "Q": "Queens", "R": "Staten Island"}

# Court sports we surface (hard courts / "things to play on"), label + key.
COURT_SPORTS = [
    ("basketball", "Basketball"),
    ("handball", "Handball"),
    ("tennis", "Tennis"),
    ("pickleball", "Pickleball"),
    ("volleyball", "Volleyball"),
    ("bocce", "Bocce"),
]


def fetch(dataset_id, params):
    params = dict(params)
    params["$limit"] = 50000
    url = BASE.format(dataset_id) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "nyc-playground-explorer"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def centroid(geom):
    """Approximate centroid: mean of the outer-ring vertices across polygons."""
    if not geom:
        return None
    xs, ys = [], []
    coords = geom.get("coordinates", [])
    gtype = geom.get("type")
    polys = coords if gtype == "MultiPolygon" else [coords]
    for poly in polys:
        if not poly:
            continue
        ring = poly[0]  # exterior ring
        for x, y in ring:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return [round(sum(ys) / len(ys), 6), round(sum(xs) / len(xs), 6)]


def build():
    places = []

    # --- Playgrounds (children's play equipment) ---
    dca = fetch(DCA_ID, {})
    for row in dca:
        c = centroid(row.get("shape"))
        if not c:
            continue
        places.append({
            "lat": c[0], "lon": c[1],
            "name": row.get("publicname", "Playground").strip(),
            "loc": (row.get("publiclocation") or "").strip(),
            "boro": BORO.get(row.get("borough", ""), row.get("borough", "")),
            "kind": "playground",
            "sports": [],
            "acc": False,
        })

    # --- Park name + location lookup (joined by gispropnum) ---
    parks = {}
    for row in fetch(PROP_ID, {"$select": "gispropnum,signname,location,name311"}):
        gid = row.get("gispropnum")
        if gid:
            parks[gid] = {
                "name": (row.get("signname") or row.get("name311") or "").strip(),
                "loc": (row.get("location") or "").strip(),
            }

    # --- Athletic courts ---
    where = ("featurestatus='Active' AND ("
             + " OR ".join(f"{k}=true" for k, _ in COURT_SPORTS) + ")")
    ath = fetch(ATH_ID, {"$where": where})
    for row in ath:
        c = centroid(row.get("multipolygon"))
        if not c:
            continue
        sports = [label for key, label in COURT_SPORTS
                  if str(row.get(key)).lower() == "true"]
        if not sports:
            continue
        park = parks.get(row.get("gispropnum"), {})
        name = park.get("name") or (sports[0] + " courts")
        places.append({
            "lat": c[0], "lon": c[1],
            "name": name,
            "loc": park.get("loc", ""),
            "boro": BORO.get(row.get("borough", ""), row.get("borough", "")),
            "kind": "court",
            "sports": sports,
            "acc": str(row.get("accessible")).lower() == "true",
            "surface": (row.get("surface_type") or "").strip(),
            "dim": (row.get("dimensions") or "").strip(),
        })

    with open("data/places.json", "w") as f:
        json.dump(places, f, separators=(",", ":"))

    # Summary
    pg = sum(1 for p in places if p["kind"] == "playground")
    ct = sum(1 for p in places if p["kind"] == "court")
    print(f"Playgrounds: {pg}")
    print(f"Courts: {ct}")
    for key, label in COURT_SPORTS:
        n = sum(1 for p in places if label in p["sports"])
        print(f"  {label}: {n}")
    print(f"Total places: {len(places)}")


if __name__ == "__main__":
    build()
