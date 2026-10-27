#!/usr/bin/env python3
"""Build a cleaned, validator-friendly TGSRTC GTFS feed from the official open-data feed.

Modelled on the community BMTC feed (github.com/Vonter/bmtc-gtfs, Mobility Database mdb-2595).
Timetables are untouched: every trip, stop time and shape point comes from TGSRTC's own feed.

Cleaning:
  stops      clean Title Case names, "Twd X" moved to stop_desc as "(Towards X)",
             same-name platforms within 600 m grouped under a parent station
  routes     long name without the duplicated short name, "Origin → Destination (via X)",
             short names like "90D_JBS_DSNR_BDG" cut to "90D", identical duplicate routes merged
  trips      trip_headsign = clean name of the last stop; noisy trip_short_name dropped
  stop_times shape_dist_traveled blanked on trips where TGSRTC's distances go backwards
  shapes     shape_dist_traveled added (km, same unit as stop_times)
  extras     feed_info.txt and attributions.txt crediting TGSRTC

Usage: G=data/new/g/ OUT=gtfs/tgsrtc python3 scripts/build_gtfs.py
Contains data provided by TGSRTC. Unofficial; not endorsed by TGSRTC.
"""
import csv, re, os, math, collections, zipfile

G = os.environ.get('G', 'data/new/g/')
OUT = os.environ.get('OUT', 'gtfs/tgsrtc')
os.makedirs(OUT, exist_ok=True)
TW = re.compile(r'\s*[-,]?\s*((?<=[a-z])twds?(?=\s)|\b(?:twds?|towards)\b)\.?\s*(.*)$', re.I)
ACRONYMS = {'CBS', 'JBS', 'MGBS', 'ECIL', 'JNTU', 'BHEL', 'HCL', 'HCU', 'KPHB', 'NIMS', 'MMTS', 'ORR', 'IDPL',
            'HMT', 'NGRI', 'CCMB', 'IICT', 'NFC', 'DRDO', 'DRDL', 'RTC', 'TSRTC', 'TGSRTC', 'HPS', 'ISB', 'IIIT',
            'HAL', 'BDL', 'MLA', 'GHMC', 'SBI', 'NTR', 'KBR', 'IKEA', 'DLF', 'TCS', 'AOC', 'RGIA', 'SR', 'BHEL'}


def tidy(s):
    s = re.sub(r'\s+', ' ', s).strip(' -,')
    def w(t):
        if t.upper().strip('.') in ACRONYMS:
            return t.upper()
        return t[:1].upper() + t[1:].lower()
    return ' '.join(w(t) for t in s.split(' '))


def split_twd(name):
    m = TW.search(name)
    if not m:
        return tidy(name), ''
    return tidy(name[:m.start()]), tidy(m.group(2))


def dist(a, b, c, d):
    x = math.radians(d - b) * math.cos(math.radians((a + c) / 2))
    return 6371.0 * math.hypot(x, math.radians(c - a))


def rd(f):
    return list(csv.DictReader(open(os.path.join(G, f), encoding='utf-8-sig')))


def wr(f, cols, rows):
    with open(os.path.join(OUT, f), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(cols)
        w.writerows(rows)


# ---- stops + parent stations
stops = rd('stops.txt')
info = {}
for s in stops:
    base, tow = split_twd(s['stop_name'])
    info[s['stop_id']] = (base, tow, float(s['stop_lat']), float(s['stop_lon']), s['zone_id'].strip())
byname = collections.defaultdict(list)
for sid, v in info.items():
    byname[v[0].lower()].append(sid)
parent = {}
stations = []
for ids in byname.values():
    par = {i: i for i in ids}
    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = info[ids[i]], info[ids[j]]
            if dist(a[2], a[3], b[2], b[3]) <= 0.6:
                par[f(ids[i])] = f(ids[j])
    groups = collections.defaultdict(list)
    for i in ids:
        groups[f(i)].append(i)
    for grp in groups.values():
        if len(grp) < 2:
            continue
        key = 'S_' + min(grp)
        la = sum(info[i][2] for i in grp) / len(grp)
        lo = sum(info[i][3] for i in grp) / len(grp)
        stations.append([key, info[grp[0]][0], '', '', '%.6f' % la, '%.6f' % lo, '1', ''])
        for i in grp:
            parent[i] = key
srows = []
for s in stops:
    base, tow, la, lo, zone = info[s['stop_id']]
    desc = '%s (Towards %s)' % (base, tow) if tow else ''
    srows.append([s['stop_id'], base, desc, zone, s['stop_lat'], s['stop_lon'], '0', parent.get(s['stop_id'], '')])
wr('stops.txt', ['stop_id', 'stop_name', 'stop_desc', 'zone_id', 'stop_lat', 'stop_lon', 'location_type', 'parent_station'],
   stations + srows)

# ---- trips (needed for route short-name fallback)
trips = rd('trips.txt')
first_tsn = {}
for t in trips:
    first_tsn.setdefault(t['route_id'], t['trip_short_name'])

# ---- routes
routes = rd('routes.txt')
def short(r):
    s = r['route_short_name'].strip()
    if s == r['route_id'] and first_tsn.get(r['route_id']):
        s = first_tsn[r['route_id']]
    s = re.split(r'_', s)[0].strip()
    if len(s) > 12 and ' ' in s:
        s = s.split(' ')[0]
    return s
def long_name(r, sn):
    ln = r['route_long_name'].strip()
    ln = re.sub(r'^\s*' + re.escape(r['route_short_name'].strip()) + r'\s*-\s*', '', ln)
    ln = re.sub(r'^\s*' + re.escape(sn) + r'\s*-\s*', '', ln)
    parts = re.split(r'\s+to\s+', ln, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return tidy(ln)
    o, ov = split_twd(parts[0])
    d, dv = split_twd(parts[1])
    via = ', '.join(v for v in (ov, dv) if v)
    out = '%s → %s' % (o, d)
    return out + (' (via %s)' % via if via else '')
rmap, seen, rrows = {}, {}, []
for r in routes:
    sn = short(r)
    ln = long_name(r, sn)
    k = (sn, ln)
    if k in seen:
        rmap[r['route_id']] = seen[k]
        continue
    seen[k] = r['route_id']
    rmap[r['route_id']] = r['route_id']
    rrows.append([r['route_id'], 'TGSRTC', sn, ln, '3'])
wr('routes.txt', ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type'], rrows)

# ---- stop_times
st = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(G, 'stop_times.txt'), encoding='utf-8-sig')):
    st[r['trip_id']].append(r)
bad = 0
shape_of = {t['trip_id']: t['shape_id'] for t in trips}
strows = []
trip_max = collections.defaultdict(float)
headsign = {}
for t in trips:
    rows = sorted(st[t['trip_id']], key=lambda r: int(r['stop_sequence']))
    ds = [r['shape_dist_traveled'] for r in rows]
    ok = all(ds) and all(float(b) > float(a) for a, b in zip(ds, ds[1:]))
    if not ok:
        bad += 1
    headsign[t['trip_id']] = info[rows[-1]['stop_id']][0]
    if ok:
        trip_max[t['shape_id']] = max(trip_max[t['shape_id']], float(ds[-1]))
    for r in rows:
        strows.append([t['trip_id'], r['arrival_time'], r['departure_time'], r['stop_id'], r['stop_sequence'],
                       r['timepoint'], r['shape_dist_traveled'] if ok else ''])
wr('stop_times.txt', ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'timepoint',
                      'shape_dist_traveled'], strows)
del strows, st

wr('trips.txt', ['route_id', 'service_id', 'trip_id', 'trip_headsign', 'direction_id', 'shape_id'],
   [[rmap[t['route_id']], t['service_id'], t['trip_id'], headsign[t['trip_id']], t['direction_id'], t['shape_id']]
    for t in trips])

# ---- shapes with distance, simplified (Ramer-Douglas-Peucker, 2 m) so the zip fits on GitHub.
# Distances are measured on the full-resolution shape before simplifying.
TOL = float(os.environ.get('SHAPE_TOL_M', '2'))
def rdp(pts):
    if len(pts) < 3:
        return list(range(len(pts)))
    la0 = math.radians(float(pts[0][1]))
    xy = [(math.radians(float(lo)) * math.cos(la0) * 6371000, math.radians(float(la)) * 6371000) for _, la, lo in pts]
    keep = [False] * len(xy)
    keep[0] = keep[-1] = True
    stack = [(0, len(xy) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = xy[a], xy[b]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        best, bi = -1, -1
        for i in range(a + 1, b):
            x, y = xy[i]
            if L2 == 0:
                d = math.hypot(x - x1, y - y1)
            else:
                t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
                d = math.hypot(x - x1 - t * dx, y - y1 - t * dy)
            if d > best:
                best, bi = d, i
        if best > TOL:
            keep[bi] = True
            stack += [(a, bi), (bi, b)]
    return [i for i, k in enumerate(keep) if k]

sh = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(G, 'shapes.txt'), encoding='utf-8-sig')):
    sh[r['shape_id']].append((int(r['shape_pt_sequence']), r['shape_pt_lat'], r['shape_pt_lon']))
shrows = []
for sid, pts in sh.items():
    pts.sort()
    clean, cum, tot, prev = [], [], 0.0, None
    for seq, la, lo in pts:
        if prev:
            if (la, lo) == prev:
                continue  # duplicate consecutive point
            tot += dist(float(prev[0]), float(prev[1]), float(la), float(lo))
        prev = (la, lo)
        clean.append((seq, la, lo))
        cum.append(tot)
    # stop_times distances are TGSRTC's, rounded to 10 m; stretch the shape by the tiny
    # difference so no trip runs past the end of its shape
    k = trip_max.get(sid, 0) / tot if tot else 1
    k = k + 1e-6 if k > 1 else 1
    KMAX = max(globals().get('KMAX', 1), k)
    keep = rdp(clean)
    for i in keep:
        (seq, la, lo), c = clean[i], cum[i]
        shrows.append([sid, la, lo, seq, '%.5f' % (c * k)])
wr('shapes.txt', ['shape_id', 'shape_pt_lat', 'shape_pt_lon', 'shape_pt_sequence', 'shape_dist_traveled'], shrows)
del shrows

# ---- agency, calendar, feed_info, attributions
ag = rd('agency.txt')[0]
wr('agency.txt', ['agency_id', 'agency_name', 'agency_url', 'agency_timezone', 'agency_lang'],
   [[ag['agency_id'], ag['agency_name'], ag['agency_url'], ag['agency_timezone'], ag['agency_lang']]])
cal = rd('calendar.txt')
cols = ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date']
wr('calendar.txt', cols, [[c[k] for k in cols] for c in cal])
fi = rd('feed_info.txt')[0]
REPO = 'https://github.com/deekshithbangi/hyderabad-transit-finder'
wr('feed_info.txt', ['feed_publisher_name', 'feed_publisher_url', 'feed_lang', 'feed_start_date', 'feed_end_date',
                     'feed_version', 'feed_contact_url'],
   [['Hyderabad Transit Finder', REPO, 'en', fi['feed_start_date'], fi['feed_end_date'], fi['feed_version'], REPO + '/issues']])
wr('attributions.txt', ['attribution_id', 'organization_name', 'is_producer', 'is_operator', 'is_authority', 'attribution_url'],
   [['tgsrtc', 'Telangana State Road Transport Corporation', '1', '1', '1', 'https://tgsrtc.telangana.gov.in/open-data'],
    ['transitfinder', 'Hyderabad Transit Finder', '1', '', '', REPO]])

files = ['agency.txt', 'attributions.txt', 'calendar.txt', 'feed_info.txt', 'routes.txt', 'shapes.txt', 'stop_times.txt',
         'stops.txt', 'trips.txt']
zp = OUT.rstrip('/') + '.zip'
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in files:
        z.write(os.path.join(OUT, f), f)
print('max shape stretch %.4f' % KMAX)
print('stations', len(stations), 'routes', len(rrows), 'merged', len(routes) - len(rrows),
      'trips w/o dist', bad, '->', zp)
