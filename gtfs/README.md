# TGSRTC GTFS (cleaned)

A cleaned, validator-friendly GTFS Schedule feed for TGSRTC Hyderabad city buses, built from the official TGSRTC open-data feed (version 20260901, valid 1 Sep 2026 to 1 Sep 2031). Modelled on the community [BMTC GTFS](https://github.com/Vonter/bmtc-gtfs) feed.

**Download:** [`tgsrtc.zip`](tgsrtc.zip)

Contains data provided by TGSRTC. This is an unofficial repackaging and is not endorsed by TGSRTC. Source: https://tgsrtc.telangana.gov.in/open-data

## What's inside

| File | Rows | Notes |
|---|---|---|
| agency.txt | 1 | TGSRTC |
| attributions.txt | 2 | TGSRTC (producer, operator, authority) and this repackaging |
| calendar.txt | 1 | Daily service |
| feed_info.txt | 1 | Publisher and version |
| routes.txt | 3,914 | Clean names like `Koti Womens College → Ibrahimpatnam Bus Station` |
| stops.txt | 5,177 stops + 1,700 stations | Clean names, direction in `stop_desc`, platforms grouped under stations |
| trips.txt | 51,985 | With `trip_headsign` |
| stop_times.txt | 1,286,284 | Official times, untouched |
| shapes.txt | ~1.08M points | With `shape_dist_traveled` in km, simplified to within 2 m |

`stop_times.txt` and `shapes.txt` are too large to keep in git uncompressed, so they are only in the zip.

## What was cleaned

Timetables are not changed. Every trip, stop time and shape point comes from TGSRTC's feed.

- **Stops:** Title Case names with "Twd X" removed from the name; the direction goes into `stop_desc` as `Shalibanda (Towards Charminar)`. Same-name stops within 600 m are grouped under a parent station (`location_type=1`).
- **Routes:** the short name is no longer repeated in the long name; long names read `Origin → Destination (via X)`; 62 routes whose short name was an internal ID get the real number from the trip name; codes like `90D_JBS_DSNR_BDG` become `90D`; 219 exact duplicate routes are merged.
- **Trips:** `trip_headsign` added (the last stop); the noisy `trip_short_name` is dropped.
- **Shapes:** duplicate points removed and lines simplified to within 2 m of the original (3.0M → 1.08M points) so the zip stays under GitHub's limits. `shape_dist_traveled` is measured on the full-resolution line.
- **Distances:** it is blanked on the 2,791 trips where the official stop distances go backwards.
- **Metadata:** `feed_info.txt` and `attributions.txt` added.

## Validation

Checked with the MobilityData GTFS Validator 8.0.1. See [validation.md](validation.md).

## Rebuild

```bash
G=path/to/official_gtfs/ OUT=gtfs/tgsrtc python3 scripts/build_gtfs.py
```
