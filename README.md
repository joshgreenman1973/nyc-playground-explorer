# NYC Playground & Court Explorer

An interactive map of every public playground and recreational court across New
York City — children's play areas (swings, slides, climbers), plus basketball,
handball (NYC's racquetball-style courts), tennis, pickleball, volleyball and
bocce courts.

**Live:** https://joshgreenman1973.github.io/nyc-playground-explorer/

## Features

- 5,081 places across all five boroughs, clustered for fast browsing
- Filter by amenity type, borough, and wheelchair accessibility
- Search by park name or street
- "Find near me" geolocation
- One-tap directions to any spot via Google Maps

## Data

NYC Department of Parks & Recreation, via NYC Open Data. See
[METHODOLOGY.md](METHODOLOGY.md) for sources, definitions and limits.

## Rebuild

```
python3 build_data.py   # regenerates data/places.json
```

Pure static site — open `index.html` or serve the folder.
