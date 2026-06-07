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
- **Playground density by neighborhood** choropleth (playgrounds per square mile
  across 262 neighborhoods) with a live ranking
- **Address autocomplete** (free NYC GeoSearch) that counts every playground and
  court within a 10-minute (½-mile) walk
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
