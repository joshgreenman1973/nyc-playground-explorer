# NYC Playground & Court Explorer

An interactive map of every public playground and recreational court across New
York City — children's play areas (swings, slides, climbers), plus basketball,
handball (NYC's racquetball-style courts), tennis, pickleball, volleyball and
bocce courts.

**Live:** https://joshgreenman1973.github.io/nyc-playground-explorer/

## Features

- 5,081 places across all five boroughs, clustered for fast browsing
- **Actual facility shapes** — zoom in and every court / play area is drawn as
  its real mapped polygon, not a dot
- **Hover tooltips** with name, type, surface and accessibility
- **Neighborhood density** choropleth with three comparable metrics — playgrounds
  per square mile, children per square mile, and **children per playground** —
  across 262 neighborhoods, each with a live ranking
- **Address autocomplete** (free NYC GeoSearch) that counts the playgrounds and
  parks within a **10- or 20-minute walk**; each park is counted once even if it
  holds many courts
- Filter by amenity type, borough, and wheelchair accessibility
- "Use my location" geolocation and one-tap Google Maps directions

## Data

NYC Department of Parks & Recreation, via NYC Open Data. See
[METHODOLOGY.md](METHODOLOGY.md) for sources, definitions and limits.

## Rebuild

```
python3 build_data.py   # regenerates data/places.json
```

Pure static site — open `index.html` or serve the folder.
