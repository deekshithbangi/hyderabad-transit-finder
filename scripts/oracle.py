# Raw-GTFS oracle: direct trips between two stop-name substrings after a time. usage: python3 oracle.py "tarnaka" "secunderabad" 09:00
import csv,sys,collections,re
G='data/new/g/'; a,b,t=sys.argv[1].lower(),sys.argv[2].lower(),sys.argv[3]
h,m=map(int,t.split(':')); t0=h*60+m
S={s['stop_id']:s['stop_name'] for s in csv.DictReader(open(G+'stops.txt'))}
A={k for k,v in S.items() if re.match(re.escape(a)+r'\b',v.lower())}; B={k for k,v in S.items() if re.match(re.escape(b)+r'\b',v.lower())}
R={r['route_id']:r for r in csv.DictReader(open(G+'routes.txt',encoding='utf-8-sig'))}
T={x['trip_id']:x for x in csv.DictReader(open(G+'trips.txt'))}
def mn(x): h,m,s=map(int,x.split(':')); return h*60+m
st=collections.defaultdict(list)
for r in csv.DictReader(open(G+'stop_times.txt')):
    if r['stop_id'] in A or r['stop_id'] in B: st[r['trip_id']].append((int(r['stop_sequence']),r['stop_id'],mn(r['departure_time'])))
res=[]
for tid,l in st.items():
    l.sort()
    for i,(q,s,d) in enumerate(l):
        if s in A and d>=t0:
            for q2,s2,d2 in l[i+1:]:
                if s2 in B: 
                    tr=T[tid]; r=R[tr['route_id']]['route_short_name']
                    if r==tr['route_id']: r=tr['trip_short_name'].split('_')[0]
                    res.append((d2,d,r,S[s],S[s2])); break
            break
res.sort()
seen=set()
for x in res:
    if x[2] in seen: continue
    seen.add(x[2]); print('%02d:%02d dep %02d:%02d arr  %s  %s -> %s'%(x[1]//60,x[1]%60,x[0]//60,x[0]%60,x[2],x[3],x[4]))
    if len(seen)>=8: break
