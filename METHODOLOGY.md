# Methodology — NYC Playground & Court Explorer

A map of every public playground and recreational court across New York City's
five boroughs. Nothing here is a black box — this document explains exactly
what is shown, where it comes from and what the limits are.

## Data sources

All data is from the New York City Department of Parks & Recreation (DPR),
published on the NYC Open Data portal. Two datasets are combined.

| Layer | Dataset | ID | Records used |
|-------|---------|----|----|
| NYC Parks playgrounds | [Playgrounds with Dedicated Children's Areas (DCAs)](https://data.cityofnewyork.us/d/j55h-3upk) | `j55h-3upk` | 1,010 |
| School playgrounds | [Schoolyards to Playgrounds](https://data.cityofnewyork.us/d/dbmp-698d) | `bbtf-6p3c` | 294 |
| NYCHA playgrounds | [OpenStreetMap](https://www.openstreetmap.org/copyright) ∩ [NYCHA Developments](https://data.cityofnewyork.us/d/phvi-damg) | `phvi-damg` | 122 |
| Courts | [Athletic Facilities](https://data.cityofnewyork.us/d/qnem-b8re) | `qnem-b8re` | 4,072 |
| Condition grades | [Parks Inspection Program – Inspections](https://data.cityofnewyork.us/d/yg3y-7juh) | `yg3y-7juh` | 2025–26 |
| Playground accessibility | NYC Parks accessibility classification (Levels 1–4) | `a4qt-mpr5` | 727 accessible |
| Court lighting | Athletic Facilities `field_lighted` | `qnem-b8re` | 179 lit |
| Spray showers / sprinklers | [NYC Parks Spray Showers](https://data.cityofnewyork.us/d/ckaz-6gaa) | `ckaz-6gaa` | 1,112 |
| Outdoor pools | NYC Parks Directory of Outdoor Pools | `fx7a-24mf` | 79 |
| Recreation centers | NYC Parks Directory of Recreation Centers | `ydj7-rk56` | 46 |
| Park names & cross streets | [Parks Properties](https://data.cityofnewyork.us/d/enfh-gkve) | `enfh-gkve` | join key |
| Neighborhood boundaries & area | [2020 Neighborhood Tabulation Areas](https://data.cityofnewyork.us/d/9nt8-h7nd) | `9nt8-h7nd` | 262 NTAs |
| Tract → neighborhood crosswalk | [2020 Census Tracts to 2020 NTAs](https://data.cityofnewyork.us/d/hm78-6dwm) | `hm78-6dwm` | join key |
| Child & total population | 2020 U.S. Census (PL 94-171), `api.census.gov` | `dec/pl` | by tract |

Data pulled on 2026-06-07. The DCA and Athletic Facilities datasets are
refreshed by DPR (last updated May 2026 at time of build).

## What counts as a "playground"

Playgrounds are drawn from **three public sources**, colour-coded on the map and
toggleable separately. Together they total **1,426** public playgrounds.

**1. NYC Parks playgrounds (1,010).** NYC Parks deliberately distinguishes a
**Dedicated Children's Area (DCA)** from a "playground," because a property
labeled "playground" may actually contain only fitness equipment or courts. A
DCA is a space with **play equipment designed for children** — structures,
climbers, slides, swings, spray showers. This is the authoritative layer and is
never de-duplicated.

**2. School playgrounds open to the public (294).** From the
**Schoolyards to Playgrounds** program, which opens DOE schoolyards to the
public outside school hours (evenings, weekends, holidays). Mapped polygons.

**3. NYCHA playgrounds (122).** New York City has **no published inventory** of
NYCHA playgrounds. As the best available proxy, we take every
`leisure=playground` feature mapped by **OpenStreetMap** contributors and keep
those whose location falls **inside a NYCHA development boundary**
(`phvi-damg`). These render as small circles rather than polygons because OSM
gives a point, not a footprint.

**De-duplication.** School and NYCHA candidates are dropped when they sit within
~60 m of a playground already counted, so a site that appears in more than one
source is counted once. Parks DCAs are always kept.

## What counts as a "court"

From the Athletic Facilities dataset, we keep only facilities that are:

- **`featurestatus = 'Active'`** (excludes Removed, Inactive, Archived and
  Temporarily Closed facilities — about 1,000 records dropped), and
- flagged for at least one of these court sports:
  **basketball, handball, tennis, pickleball, volleyball, bocce.**

Ball fields (baseball, soccer, football, etc.) are intentionally excluded — the
map is about "things to play *on*": playgrounds and hard courts.

A single facility record can carry more than one sport flag (e.g. a court
striped for both tennis and pickleball). All sports on a record are shown as
tags in its popup, and the marker appears under every relevant filter.

### Handball = New York City's racquetball

NYC Parks does not maintain a "racquetball" category. The city's wall-ball
courts are catalogued as **handball courts**, which serve the same racquetball /
wall-sport role. They are labelled "Handball courts" on the map.

### Why one park can show many markers / shapes

In the Athletic Facilities dataset **each individual court is its own record**.
A park with ten tennis courts (e.g. Crocheron Park in Queens) therefore appears
as ten separate facilities, all sharing the same park name. This is not
duplication — each marker is a real, distinct court. Zoom in past street level
and every facility is drawn as its **actual mapped shape** (the court outline),
which makes the count of side-by-side courts obvious. The "places shown" counter
counts individual facilities, not parks.

## Counts by court type (active facilities)

| Sport | Facilities |
|-------|-----------|
| Handball | 1,859 |
| Basketball | 1,437 |
| Tennis | 591 |
| Volleyball | 113 |
| Bocce | 49 |
| Pickleball | 41 |

(Totals overlap where a facility supports multiple sports.)

## Geography

At city and borough zoom levels each facility is plotted at the **approximate
centroid** of its mapped shape (the mean of its outline vertices) and grouped
into clusters for fast browsing. **Zoom in to street level (zoom 15+) and each
facility is drawn as its actual polygon shape** — the real court or play-area
outline from the source geometry. One record with no usable geometry was
dropped, leaving 5,081 places mapped.

For courts, the park **name** and **cross-street location** shown in the popup
are joined from the Parks Properties dataset on the shared `gispropnum`
(GIS property number). A handful of facilities whose property number has no
match fall back to a generic name (e.g. "Basketball courts").

## Accessibility

The "Wheelchair-accessible courts only" filter uses the Athletic Facilities
`accessible` flag. **This flag exists only on the courts dataset** — the DCA
playground layer carries no accessibility field, so playgrounds are hidden when
that filter is on. Absence of a flag does not prove a facility is inaccessible;
it means DPR has not recorded it as accessible in this dataset.

## Neighborhood density (three comparable metrics)

The density layer shades each of the city's 262 2020 Neighborhood Tabulation
Areas (NTAs — City Planning's standard neighborhood unit). A segmented control
switches between three metrics so you can **compare playground supply to where
the children actually are**:

**1. Playgrounds per square mile** — spatial density.
- All 1,426 playgrounds (Parks + school + NYCHA) are assigned to the NTA that
  geometrically contains their centroid (point-in-polygon, Shapely).
- NTA land area comes from its `shape_area` field (square feet, NYC State Plane)
  ÷ 27,878,400 = square miles.
- Density = playgrounds ÷ square miles. Densest: Chinatown–Two Bridges (≈46/sq
  mi), the Lower East Side and East Harlem; sparsest: low-rise Staten Island and
  outer Queens.

**2. Children per square mile** — where kids live.
- Children = residents **under 18** from the 2020 Census (PL 94-171): total
  population (`P1_001N`) minus the 18-and-over population (`P3_001N`), at the
  census-tract level.
- Tracts are aggregated to 2020 NTAs using the official tract→NTA crosswalk
  (`hm78-6dwm`); 2020 tracts nest cleanly inside 2020 NTAs. Citywide total:
  **1,740,142 children**.
- Density = children ÷ square miles.

**3. Children per playground** — the supply-vs-demand comparison.
- Children in an NTA ÷ all public playgrounds (Parks + school + NYCHA) in that
  NTA. Higher means each playground serves more kids. Neighborhoods that have
  children but **zero** public playgrounds are flagged in the darkest colour.
- Adding school and NYCHA playgrounds materially changes the picture. Borough
  Park, which looked extreme on Parks data alone (≈40,000 children, 2 Parks
  playgrounds), has 8 public playgrounds once schoolyards and NYCHA are
  included — ~5,000 kids each. The most stretched residential neighborhoods are
  now the **Upper East Side–Carnegie Hill**, **North Corona**, **Central
  Astoria** and **Tribeca**.
- **Caveat — NYCHA coverage is OpenStreetMap-dependent.** Because there is no
  official NYCHA playground dataset, the NYCHA layer is only as complete as
  OpenStreetMap's mapping of those developments. Some real NYCHA play areas are
  missing (e.g. Co-op City — actually a Mitchell-Lama, not NYCHA — still shows
  zero), and private, religious-school and other play areas remain out of scope
  entirely. A high ratio signals "few *mapped public* playgrounds per child," a
  starting question rather than a verdict.

All three sidebar rankings are restricted to **residential NTAs** (type `0`),
excluding park, cemetery, airport and other non-residential tabulation areas
whose figures are not meaningful.

## Condition grades (2025–26)

Every site carries its most recent **Parks Inspection Program (PIP)** overall
condition rating, but only from inspections in **2025 or 2026** — older ratings
are deliberately not shown. PIP grades are binary:

- **A — Acceptable**
- **U — Unacceptable**
- (rows graded "N / not rated" are skipped, so the grade reflects the latest real
  A/U inspection in the window)

Inspections in the dataset run from **Feb 2025 through Feb 2026**. Grades are
joined to each playground and court by property ID: first the site's own
sub-property ID (`omppropid`), then its parent property (`gispropnum`), then the
most recent rating among any sub-site of that park. This covers **91%** of mapped
places (5,003 of 5,498); the rest were not inspected in the 2025–26 window and
show as "not rated." Across inspected sites, **about 84% are rated Acceptable.**

Toggle **"Color by 2025–26 condition grade"** to recolour every marker and shape
green (Acceptable) / red (Unacceptable) / grey (not rated). The grade and
inspection month also appear in each site's hover tooltip and popup.

**Caveats.** PIP rates a *site's* overall condition (cleanliness, structures,
safety surface, glass, graffiti, etc.) on the inspection day — it is a snapshot,
not a running average, and "Acceptable" is a floor, not a quality score. NYCHA
playgrounds (sourced from OpenStreetMap, not NYC Parks) are **not** in PIP and so
always show as "not rated."

## Accessibility (disability-friendly playgrounds)

NYC Parks classifies playground accessibility on a **four-level scale**, shown as
a badge in each playground's popup and filterable with "Show only accessible
sites":

1. **Playgrounds for All Children**
2. **Accessible Playgrounds**
3. Accessible **+ universally accessible swings**
4. Accessible **+ transfer platforms and ground-level play features** (the most
   inclusive)

**727 of the 1,010 NYC Parks playgrounds are accessible** (484 at Level 4, 134 at
Level 2, 94 at Level 3, 13 at Level 1). The classification is joined to each
playground by location (nearest match within ~120 m; 93% of Parks playgrounds
matched).

**Caveats.** (1) This is a *structural* classification — built features like
transfer platforms don't change often, but the published source predates 2025,
so treat it as "how this playground was last classified," not a fresh audit.
(2) It exists for **NYC Parks playgrounds only** — school and NYCHA playgrounds
have no accessibility data here and are not marked. (3) Courts carry NYC Parks'
own `accessible` flag, but it is barely populated (only ~12 of 5,850 active
facilities), so absence of a wheelchair badge on a court means "not recorded,"
not "inaccessible." Lit courts (for evening play) are flagged from the
`field_lighted` field — 179 of them.

## The statistics strip

The strip across the top of the map summarises the analysis at a glance: total
public playgrounds (with the Parks / school / NYCHA split), the densest and
sparsest (non-zero) residential neighborhoods, the most "stretched" neighborhood
by children per playground, how many residential neighborhoods have children but
no mapped public playground, and the citywide **median** of ~1,500 children per
playground. All figures use the residential-NTA set described above.

## "Parks within a 10-minute walk"

Type any New York City address (autocomplete is provided free by the
[NYC Planning GeoSearch](https://geosearch.planninglabs.nyc) service, which is
NYC-only and requires no API key) or tap "Use my location." Choose a **10-minute
(½-mile)** or **20-minute (1-mile)** walk. The map then draws the radius and
reports how many playgrounds and how many parks-with-courts fall inside it, with
a distance-sorted list.

**Counting rule — each park counted once.** Facilities are grouped by their park
property ID before counting, so a single playground that also has, say, five
handball courts counts as **one playground** (and one park with courts), not six
separate items. This is why the nearby list shows each park name only once even
though the underlying data stores every court as its own record.

**Walking distance follows the street network, not a straight line.** When you
enter an address, the map requests a pedestrian **isochrone** — the actual area
reachable on foot in 10 or 20 minutes along real streets — from the free,
no-key Valhalla routing service hosted by FOSSGIS (built on OpenStreetMap). The
playground and court counts are then everything whose location falls inside that
walk-shed. Because it routes along streets and around barriers (highways,
rivers, rail yards), it is more realistic — and usually smaller — than a plain
circle: e.g. near 100 Gold Street the street-network 10-minute walk reaches 5
playgrounds where a ½-mile circle suggested 6. If the routing service is
unavailable, the map falls back to a straight-line ½-mile (10 min) / 1-mile
(20 min) circle and says so. The distances listed for each result are
straight-line, as a rough sort order.

## Water & recreation layers

Three additional toggleable layers (under "Water & recreation"):

- **Spray showers / sprinklers (1,112)** — NYC Parks summer water-play features.
  Off by default because of their number; toggle on to show them.
- **Outdoor pools (79)** — NYC Parks free outdoor pools, with size and wheelchair
  accessibility in the popup.
- **Recreation centers (46)** — NYC Parks rec centers; located by joining their
  property ID to Parks Properties geometry (8 of 54 had no matching geometry and
  are omitted).

These layers are **not** counted in the playground/court walk totals or the
neighborhood density metrics — they are reference layers only.

## Known limitations

- **Playground coverage** now spans NYC Parks, public schoolyards and (via
  OpenStreetMap) NYCHA developments, but is still not exhaustive: private,
  religious-school, BID/POPS and some unmapped NYCHA play areas do not appear.
  **Court** coverage remains NYC Parks only.
- **No equipment-level detail.** The DCA layer confirms a children's play area
  exists but does not enumerate individual swings vs. slides vs. climbers. That
  granularity lives in the Parks Inspection Program feed and is not used here.
- **Status reflects DPR's records,** which may lag real-world closures,
  construction or temporary removals.
- **Centroid positions** can sit slightly off for very large or oddly shaped
  parks.

## Rebuilding the data

```
export CENSUS_API_KEY=...        # free key from census.gov/developers
python3 build_data.py            # requires the `shapely` package
```

This re-fetches the NYC Open Data datasets plus 2020 Census population and
regenerates `data/places.json` (facilities with shapes) and
`data/neighborhoods.json` (NTA boundaries with playground, child and ratio
density). The Census key is read from the environment and never stored in the
repo; without it the build still runs but skips the child-density metrics.
