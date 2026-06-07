# Methodology — NYC Playground & Court Explorer

A map of every public playground and recreational court across New York City's
five boroughs. Nothing here is a black box — this document explains exactly
what is shown, where it comes from and what the limits are.

## Data sources

All data is from the New York City Department of Parks & Recreation (DPR),
published on the NYC Open Data portal. Two datasets are combined.

| Layer | Dataset | ID | Records used |
|-------|---------|----|----|
| Children's playgrounds | [Playgrounds with Dedicated Children's Areas (DCAs)](https://data.cityofnewyork.us/d/j55h-3upk) | `j55h-3upk` | 1,010 |
| Courts | [Athletic Facilities](https://data.cityofnewyork.us/d/qnem-b8re) | `qnem-b8re` | 4,072 |
| Park names & cross streets | [Parks Properties](https://data.cityofnewyork.us/d/enfh-gkve) | `enfh-gkve` | join key |
| Neighborhood boundaries & area | [2020 Neighborhood Tabulation Areas](https://data.cityofnewyork.us/d/9nt8-h7nd) | `9nt8-h7nd` | 262 NTAs |

Data pulled on 2026-06-07. The DCA and Athletic Facilities datasets are
refreshed by DPR (last updated May 2026 at time of build).

## What counts as a "playground"

NYC Parks deliberately distinguishes a **Dedicated Children's Area (DCA)** from
a "playground." In their words, the term playground is avoided because a
property labeled "playground" may actually contain only adult fitness equipment
or handball/basketball courts and no children's play equipment at all.

A DCA is a space with **play equipment specifically designed for children** —
play structures, climbers, slides, swings and spray showers. That is exactly
the "swingsets, slides and jungle gyms" the map is meant to show, so the DCA
layer is the playground layer here. There were 1,010 active DCAs.

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

## Playground density by neighborhood

The "Playground density by neighborhood" layer shades each of the city's 262
2020 Neighborhood Tabulation Areas (NTAs — City Planning's standard
neighborhood unit) by **playgrounds per square mile**.

How it is computed (`build_data.py`):

1. Each of the 1,010 children's playgrounds is assigned to the NTA that
   geometrically contains its centroid (a point-in-polygon test using Shapely).
   All 1,010 matched an NTA.
2. Each NTA's land area is taken from its `shape_area` field (square feet, NYC
   State Plane) and converted to square miles (÷ 27,878,400).
3. Density = playgrounds ÷ area in square miles.

This is **spatial density** — how many playgrounds sit in a given amount of
ground — which is the literal reading of "playground density." It is *not* a
per-capita or per-child measure; a job-heavy or low-population neighborhood with
few playgrounds will read as low-density even if it serves few children. A
per-child provision metric would require joining current census age data to
2020 NTAs and is a possible future addition.

The ranked "most playground-dense neighborhoods" list shown in the sidebar is
restricted to **residential NTAs** (NTA type `0`), excluding park, cemetery,
airport and other non-residential tabulation areas whose density figures are not
meaningful. The densest neighborhoods are on the Lower East Side and in Upper
Manhattan and the South Bronx (roughly 15–22 playgrounds per square mile);
large, low-rise outer-borough areas — much of Staten Island, eastern Queens —
are the least dense.

Some dense residential NTAs show **zero** NYC Parks playgrounds (e.g. Co-op City,
parts of East Flatbush). This usually means the local play areas are run by
NYCHA, schools or private developments and so fall outside the Parks datasets —
see limitations below.

## "Parks within a 10-minute walk"

Type any New York City address (autocomplete is provided free by the
[NYC Planning GeoSearch](https://geosearch.planninglabs.nyc) service, which is
NYC-only and requires no API key) or tap "Use my location." The map then:

- draws a **½-mile circle** around the point, and
- counts every playground and court whose centroid falls inside it, reporting
  playgrounds, courts and the number of distinct parks, with a distance-sorted
  list.

A ½ mile is the standard planning proxy for a 10-minute walk (~3 mph). The
radius is measured **as the crow flies**, not along the street network or
accounting for barriers like highways or rivers, so the true walking catchment
is somewhat smaller. Distances shown are straight-line.

## Known limitations

- **Coverage is NYC Parks only.** Playgrounds and courts inside NYCHA
  developments, on school grounds (unless joined to Parks via Schoolyards to
  Playgrounds), in private developments, or run by other agencies are not in
  these datasets and will not appear.
- **No equipment-level detail.** The DCA layer confirms a children's play area
  exists but does not enumerate individual swings vs. slides vs. climbers. That
  granularity lives in the Parks Inspection Program feed and is not used here.
- **Status reflects DPR's records,** which may lag real-world closures,
  construction or temporary removals.
- **Centroid positions** can sit slightly off for very large or oddly shaped
  parks.

## Rebuilding the data

```
python3 build_data.py   # requires the `shapely` package
```

This re-fetches all four datasets from NYC Open Data and regenerates both
`data/places.json` (facilities with shapes) and `data/neighborhoods.json` (NTA
boundaries with playground density). No API key is required.
