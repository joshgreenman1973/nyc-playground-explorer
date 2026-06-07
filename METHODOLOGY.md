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

Each marker is plotted at the **approximate centroid** of the facility's mapped
shape (the mean of its outline vertices), computed from the multipolygon
geometry in each dataset. This is a reliable "drop a pin on this playground /
court" location, not a survey-grade coordinate. The actual entrance or gate may
be a short walk from the pin. One record with no usable geometry was dropped,
leaving 5,081 places mapped.

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
python3 build_data.py
```

This re-fetches all three datasets from NYC Open Data and regenerates
`data/places.json`. No API key is required.
