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
import os
import urllib.request
import urllib.parse
from shapely.geometry import shape, Point, mapping
from shapely.strtree import STRtree

# Census API key (free). Read from env so it never lands in the public repo.
#   export CENSUS_API_KEY=...   then run.  Without it, child-density is skipped.
CENSUS_KEY = os.environ.get("CENSUS_API_KEY", "")
NYC_COUNTIES = ["005", "047", "061", "081", "085"]  # Bronx, Kings, NY, Queens, Richmond
EQUIV_ID = "hm78-6dwm"  # 2020 census tracts -> 2020 NTA equivalency

DCA_ID, ATH_ID, PROP_ID, NTA_ID = "j55h-3upk", "qnem-b8re", "enfh-gkve", "9nt8-h7nd"
SCHOOL_ID = "bbtf-6p3c"   # Schoolyards to Playgrounds (public access out of school hours)
NYCHA_ID = "phvi-damg"    # NYCHA public housing development boundaries
PIP_ID = "yg3y-7juh"      # Parks Inspection Program inspections (condition grades)
ACCESS_ID = "a4qt-mpr5"   # carries NYC Parks playground accessibility level (1-4)
SPRAY_ID = "ckaz-6gaa"    # NYC Parks spray showers / sprinklers
POOL_URL = "https://www.nycgovparks.org/bigapps/DPR_Pools_outdoor_001.json"
REC_URL = "https://www.nycgovparks.org/bigapps/DPR_RecreationCenter_001.json"
BASE = "https://data.cityofnewyork.us/resource/{}.json"
SQFT_PER_SQMI = 27_878_400.0
DEDUP_DEG = 0.00065       # ~60 m: drop a playground this close to one already counted

OVERPASS = "https://overpass-api.de/api/interpreter"
OSM_CACHE = "data/osm_playgrounds_raw.json"

BORO = {"M": "Manhattan", "B": "Brooklyn", "X": "Bronx",
        "Q": "Queens", "R": "Staten Island",
        # NYCHA dataset uses full uppercase names
        "MANHATTAN": "Manhattan", "BROOKLYN": "Brooklyn", "BRONX": "Bronx",
        "QUEENS": "Queens", "STATEN ISLAND": "Staten Island"}

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


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nyc-playground-explorer"})
    with urllib.request.urlopen(req, timeout=120) as r:
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


def accessibility_points():
    """NYC Parks playground accessibility points: (lat, lon, is_accessible, level).

    From the dataset that carries the Parks accessibility classification
    (Level 1-4). Matched to playgrounds by location. Level meanings:
      1 Playgrounds for All Children
      2 Accessible Playgrounds
      3 + universally accessible swings
      4 + transfer platforms and ground-level play features
    """
    def lvl(s):
        for n in (4, 3, 2, 1):
            if s and f"Level {n}" in s:
                return n
        return 0
    out = []
    for r in fetch(ACCESS_ID, {"$select": "latitude,longitude,accessibility,accessibilitylevel"}):
        if r.get("latitude") and r.get("accessibility"):
            out.append((float(r["latitude"]), float(r["longitude"]),
                        r["accessibility"] == "Yes", lvl(r.get("accessibilitylevel"))))
    return out


def nearest_access(lat, lon, pts, thresh=0.0016):
    best, bd = None, thresh
    for alat, alon, acc, level in pts:
        d = abs(alat - lat) + abs(alon - lon)
        if d < bd:
            bd, best = d, (acc, level)
    return best


def pip_condition_grades():
    """Most recent 2025-26 PIP overall-condition grade per property.

    Returns (by_site, by_parent):
      by_site[prop_id]      -> {"g": "A"|"U", "d": "YYYY-MM-DD"}  (zone-specific)
      by_parent[gispropnum] -> same, most recent across all sub-sites of a park
    Only Acceptable/Unacceptable rows are kept; "N" (not rated) is ignored so the
    grade reflects the latest real inspection within the 2025-26 window.
    """
    rows = fetch(PIP_ID, {"$select": "prop_id,date,overall_condition",
                          "$where": "inspection_year IN ('2025','2026') "
                                    "AND overall_condition IN ('A','U')"})
    by_site, by_parent = {}, {}
    for r in rows:
        pid, dt, g = r.get("prop_id"), (r.get("date") or "")[:10], r.get("overall_condition")
        if not pid or not dt:
            continue
        if pid not in by_site or dt > by_site[pid]["d"]:
            by_site[pid] = {"g": g, "d": dt}
        par = pid.split("-")[0]
        if par not in by_parent or dt > by_parent[par]["d"]:
            by_parent[par] = {"g": g, "d": dt}
    return by_site, by_parent


def fetch_osm_playgrounds():
    """All OSM leisure=playground points in the NYC bbox (node + way centroids).

    Tries the live Overpass API; falls back to a cached raw file if present.
    OpenStreetMap data, © OpenStreetMap contributors, ODbL.
    """
    q = ('[out:json][timeout:120];('
         'node["leisure"="playground"](40.48,-74.28,40.93,-73.67);'
         'way["leisure"="playground"](40.48,-74.28,40.93,-73.67);'
         ');out center tags;')
    data = None
    try:
        req = urllib.request.Request(
            OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
            headers={"User-Agent": "nyc-playground-explorer/1.0 (josh.greenman@gmail.com)"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.load(r)
        with open(OSM_CACHE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"  Overpass live fetch failed ({e}); trying cache {OSM_CACHE}")
        if os.path.exists(OSM_CACHE):
            data = json.load(open(OSM_CACHE))
    if not data:
        return []
    out = []
    for e in data.get("elements", []):
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat and lon:
            out.append((round(lat, 6), round(lon, 6), e.get("tags", {}).get("name", "")))
    return out


def child_pop_by_nta():
    """Return {nta2020_code: {'pop': total, 'kids': under18}} from 2020 Census.

    under-18 = P1_001N (total) - P3_001N (18 and over), summed over the census
    tracts that make up each NTA (tracts nest cleanly inside 2020 NTAs).
    """
    if not CENSUS_KEY:
        print("WARNING: CENSUS_API_KEY not set — skipping child-density layer.")
        return {}
    # tract -> nta lookup
    tract_nta = {}
    for row in fetch(EQUIV_ID, {"$select": "geoid,ntacode"}):
        if row.get("geoid") and row.get("ntacode"):
            tract_nta[row["geoid"]] = row["ntacode"]
    # census population by tract
    out = {}
    for county in NYC_COUNTIES:
        url = ("https://api.census.gov/data/2020/dec/pl?get=P1_001N,P3_001N"
               f"&for=tract:*&in=state:36&in=county:{county}&key={CENSUS_KEY}")
        req = urllib.request.Request(url, headers={"User-Agent": "nyc-playground-explorer"})
        with urllib.request.urlopen(req, timeout=120) as r:
            rows = json.load(r)
        for tot, adult, state, cty, tract in rows[1:]:
            geoid = state + cty + tract
            nta = tract_nta.get(geoid)
            if not nta:
                continue
            kids = int(tot) - int(adult)
            d = out.setdefault(nta, {"pop": 0, "kids": 0})
            d["pop"] += int(tot)
            d["kids"] += kids
    return out


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

    # --- Playgrounds from three public sources, deduped by proximity ---
    acc_pts = accessibility_points()
    # 1. NYC Parks children's play areas (authoritative; kept first)
    pg_candidates = []
    for row in fetch(DCA_ID, {}):
        rings = rings_latlng(row.get("shape"))
        if not rings:
            continue
        c = centroid_of(rings)
        hit = nearest_access(c[0], c[1], acc_pts)
        pg_candidates.append({
            "src": "parks",
            "name": (row.get("publicname") or "Playground").strip(),
            "loc": (row.get("publiclocation") or "").strip(),
            "boro": BORO.get(row.get("borough", ""), row.get("borough", "")),
            "prop": row.get("gispropnum", ""),
            "omp": row.get("omppropid", ""),
            "acc": (hit[0] if hit else None),
            "acclvl": (hit[1] if hit and hit[0] else None),
            "c": c, "poly": rings,
        })

    # 2. Schoolyards to Playgrounds (DOE schoolyards open to the public)
    for row in fetch(SCHOOL_ID, {}):
        rings = rings_latlng(row.get("multipolygon"))
        if not rings:
            continue
        pg_candidates.append({
            "src": "school",
            "name": "School playground",
            "loc": (row.get("location") or row.get("address") or "").strip(),
            "boro": BORO.get(row.get("borough", ""), row.get("borough", "")),
            "prop": row.get("gispropnum", ""),
            "c": centroid_of(rings), "poly": rings,
        })

    # 3. OSM playgrounds that fall on NYCHA development land
    nycha_polys, nycha_boro = [], []
    for row in fetch(NYCHA_ID, {}):
        g = row.get("the_geom")
        if not g:
            continue
        try:
            nycha_polys.append(shape(g))
            nycha_boro.append(BORO.get(row.get("borough", ""), row.get("borough", "")))
        except Exception:
            pass
    nycha_tree = STRtree(nycha_polys) if nycha_polys else None
    if nycha_tree:
        for lat, lon, name in fetch_osm_playgrounds():
            pt = Point(lon, lat)
            for idx in nycha_tree.query(pt):
                if nycha_polys[idx].contains(pt):
                    pg_candidates.append({
                        "src": "nycha",
                        "name": name or "NYCHA playground",
                        "loc": "", "boro": nycha_boro[idx], "prop": "",
                        "c": [lat, lon], "poly": None,
                    })
                    break

    # Dedup by ~60 m grid so the same playground from two sources counts once.
    grid, kept = {}, []
    def cell(lat, lon):
        return (round(lat / DEDUP_DEG), round(lon / DEDUP_DEG))
    for cand in pg_candidates:
        lat, lon = cand["c"]
        cx, cy = cell(lat, lon)
        # NYC Parks DCAs are authoritative and always kept; only school/NYCHA
        # candidates are dropped when they coincide with an already-kept playground.
        if cand["src"] != "parks":
            dup = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for (klat, klon) in grid.get((cx + dx, cy + dy), []):
                        if abs(klat - lat) < DEDUP_DEG and abs(klon - lon) < DEDUP_DEG:
                            dup = True
                            break
                    if dup:
                        break
                if dup:
                    break
            if dup:
                continue
        grid.setdefault((cx, cy), []).append((lat, lon))
        kept.append(cand)

    for cand in kept:
        places.append({
            "kind": "playground", "src": cand["src"],
            "name": cand["name"], "loc": cand["loc"], "boro": cand["boro"],
            "prop": cand["prop"], "omp": cand.get("omp", ""),
            "sports": [], "acc": cand.get("acc"), "acclvl": cand.get("acclvl"),
            "surface": "", "dim": "",
            "c": cand["c"], "poly": cand["poly"],
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
            "lit": str(row.get("field_lighted")).lower() == "true",
            "surface": (row.get("surface_type") or "").strip(),
            "dim": (row.get("dimensions") or "").strip(),
            "c": centroid_of(rings), "poly": rings,
        })

    # ---------- Water & recreation layers (own toggles) ----------
    # Spray showers / sprinklers
    for row in fetch(SPRAY_ID, {}):
        pt = row.get("point")
        if not pt or not pt.get("coordinates"):
            continue
        lon, lat = pt["coordinates"][:2]
        nm = (row.get("propname") or row.get("sitename") or "Spray shower").strip()
        site = (row.get("sitename") or "").strip()
        places.append({
            "kind": "spray", "name": nm,
            "loc": ("" if site == nm else site),
            "boro": BORO.get(row.get("boro", ""), row.get("boro", "")), "prop": row.get("propnum", ""),
            "sports": [], "acc": None, "c": [round(lat, 6), round(lon, 6)], "poly": None,
        })

    # Outdoor pools
    for r in fetch_url(POOL_URL):
        if not r.get("lat") or not r.get("lon"):
            continue
        pid = r.get("Prop_ID", "")
        places.append({
            "kind": "pool", "name": (r.get("Name", "") + " Pool").strip(),
            "loc": (r.get("Location") or "").strip(),
            "boro": BORO.get(pid[:1], ""), "prop": pid,
            "sports": [], "acc": r.get("Accessible") == "Y", "size": (r.get("Size") or "").strip(),
            "c": [round(float(r["lat"]), 6), round(float(r["lon"]), 6)], "poly": None,
        })

    # Recreation centers (coords joined from Parks Properties by Prop_ID)
    rec_rows = fetch_url(REC_URL)
    rec_ids = sorted({r["Prop_ID"] for r in rec_rows if r.get("Prop_ID")})
    cmap = {}
    if rec_ids:
        inlist = ",".join("'%s'" % i for i in rec_ids)
        for row in fetch(PROP_ID, {"$select": "gispropnum,multipolygon",
                                   "$where": "gispropnum in (%s)" % inlist}):
            rings = rings_latlng(row.get("multipolygon"))
            if rings:
                cmap[row["gispropnum"]] = centroid_of(rings)
    for r in rec_rows:
        c = cmap.get(r.get("Prop_ID"))
        if not c:
            continue
        places.append({
            "kind": "rec", "name": (r.get("NAME") or "Recreation center").strip(),
            "loc": (r.get("ADDRESS") or "").strip(),
            "boro": BORO.get((r.get("Prop_ID") or "")[:1], ""), "prop": r.get("Prop_ID", ""),
            "sports": [], "acc": None, "rectype": (r.get("RecreationCenter_Type") or "").strip(),
            "c": c, "poly": None,
        })

    # ---------- Attach most-recent 2025-26 condition grade (PIP) ----------
    pip_site, pip_parent = pip_condition_grades()
    graded = 0
    for p in places:
        if p["kind"] in ("playground", "court"):
            g = (pip_site.get(p.get("omp")) or pip_site.get(p.get("prop"))
                 or pip_parent.get(p.get("prop")))
        else:
            g = None
        if g:
            p["grade"], p["graded"] = g["g"], g["d"]
            graded += 1
        else:
            p["grade"], p["graded"] = None, None
        p.pop("omp", None)  # internal join key, not needed client-side

    with open("data/places.json", "w") as f:
        json.dump(places, f, separators=(",", ":"))
    nA = sum(1 for p in places if p["grade"] == "A")
    nU = sum(1 for p in places if p["grade"] == "U")
    gradeable = sum(1 for p in places if p["kind"] in ("playground", "court"))
    print(f"Condition grades (2025-26): {graded}/{gradeable} playgrounds+courts graded "
          f"({100*graded/gradeable:.0f}%) — Acceptable {nA}, Unacceptable {nU}")

    # ---------- Neighborhood density ----------
    kids_by_nta = child_pop_by_nta()
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
        cp = kids_by_nta.get(row.get("nta2020"), {})
        metas.append({
            "name": row.get("ntaname", ""),
            "boro": row.get("boroname", ""),
            "type": row.get("ntatype", ""),     # 0 = residential; non-0 = parks/cemeteries/etc
            "area": round(area_sqmi, 4),
            "count": 0,
            "pop": cp.get("pop", 0),
            "kids": cp.get("kids", 0),
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
        kids_sqmi = round(m["kids"] / m["area"]) if m["area"] > 0 else 0
        kids_per_pg = round(m["kids"] / m["count"]) if m["count"] > 0 else None
        props = {"name": m["name"], "boro": m["boro"], "type": m["type"],
                 "count": m["count"], "area": m["area"], "per_sqmi": per_sqmi,
                 "kids": m["kids"], "pop": m["pop"],
                 "kids_sqmi": kids_sqmi, "kids_per_pg": kids_per_pg}
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
    by_src = {}
    for p in places:
        if p["kind"] == "playground":
            by_src[p["src"]] = by_src.get(p["src"], 0) + 1
    print(f"Playgrounds: {pg}  (" + ", ".join(f"{k}:{v}" for k, v in by_src.items())
          + f")   Courts: {ct}")
    for k in ("spray", "pool", "rec"):
        print(f"  {k}: {sum(1 for p in places if p['kind']==k)}")
    print(f"Total: {len(places)}")
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

    if kids_by_nta:
        total_kids = sum(m["kids"] for m in metas)
        print(f"\nTotal children (under 18) citywide: {total_kids:,}")
        served = [r for r in ranking if r["kids_per_pg"] is not None]
        served.sort(key=lambda r: r["kids_per_pg"], reverse=True)
        print("Most children PER playground (most stretched):")
        for r in served[:10]:
            print(f"  {r['kids_per_pg']:6,} kids/pg  {r['name']} ({r['boro']}) — {r['kids']:,} kids, {r['count']} pg")
        ks = sorted(r["kids_sqmi"] for r in ranking)
        print("kids/sq mi percentiles:", [ks[int(p*len(ks))] for p in (.2,.4,.6,.8,.95)])


if __name__ == "__main__":
    build()
