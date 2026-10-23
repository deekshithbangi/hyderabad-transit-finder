# Hyderabad Transit Finder

An unofficial, open-data trip planner for Hyderabad: TGSRTC city buses + Hyderabad Metro (HMRL), with walk transfers between them.

> Unofficial project. Not affiliated with or endorsed by TGSRTC or HMRL.
> Contains data provided by TGSRTC. Metro data from Open Data Telangana.

## Layout

| Path | What it is |
|---|---|
| `site/index.html` | The current Page (single self-contained file, data inlined) |
| `scripts/build_compact.py` | Builds compact bus data from a TGSRTC GTFS folder |
| `data/compact.json` | Bus data the Page uses (TGSRTC GTFS feed 20260901, Sep 2026): 3,295 cleaned stops, 4,117 route patterns, departures |
| `data/metro.json` | Metro stations, patterns, fares, and walk links to bus stops |
| `data/stop_keys.json` | Stable key per merged stop (smallest raw stop_id) |
| `data/hmrl_gtfs_2026-10-05.zip` | HMRL metro GTFS source |
| `data/stop_names.csv` | Editable stop-name sheet (fill `new_name`, keep `key`) |

Raw TGSRTC GTFS feeds are not committed (stop_times/shapes are 60–90 MB). Get them from https://data.telangana.gov.in/.

## Rebuild bus data

```bash
cd data
G=path/to/gtfs/ OUT=compact python3 ../scripts/build_compact.py
```

Optional `data/stop_name_overrides.csv` (`key,new_name`) renames stops at build time.

## Stop data format (`compact.json`)

- `stops`: `[name, lat, lon, "near X"?]`: "near X" only on names that repeat.
- `pats`: `{r: route no, h: "From → To", s: [stop idx], o: [min offset], d: [departure mins after midnight]}`.
