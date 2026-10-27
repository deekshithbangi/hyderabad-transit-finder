# Validation

MobilityData GTFS Validator 8.0.1, run on `tgsrtc.zip` on 27 Oct 2026. Full report: [validation_report.html](validation_report.html) (download and open in a browser).

**0 errors.**

| Severity | Notice | Count | Why it remains |
|---|---|---|---|
| Warning | stop_too_far_from_shape_using_user_distance | 13,771 | TGSRTC's stop distances and shapes disagree slightly; kept as published |
| Warning | mixed_case_recommended_field | 170 | Route numbers like `23GF/K` are all caps by design |
| Warning | stop_too_far_from_shape | 102 | Source shape geometry |
| Warning | fast_travel_between_consecutive_stops | 86 | Source timetable |
| Warning | fast_travel_between_far_stops | 13 | Source timetable |
| Warning | stops_match_shape_out_of_order | 1 | Source shape geometry |
| Info | trip_headsign_matches_intermediate_stop | 510 | Loop routes |
| Info | service_extends_far_in_the_future | 1 | TGSRTC publishes validity to 2031 |

The official feed had 1 error type (3,932 decreasing stop distances) and 4,133 route-name warnings plus 51,669 case warnings; those are fixed here.
