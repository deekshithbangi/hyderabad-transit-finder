# Rebuild compact.json from TGSRTC GTFS with Chalo-style stop names:
# strip "Twd X", merge same-base-name platforms within 600 m, keep platform label per pattern stop.
import csv, re, json, math, collections, statistics
import os
G=os.environ.get('G','gtfs/'); OUT=os.environ.get('OUT','compact')
def km(a,b,c,d):
    x=math.radians(d-b)*math.cos(math.radians((a+c)/2)); y=math.radians(c-a); return 6371000*math.hypot(x,y)
TW=re.compile(r'\s*[-,]?\s*((?<=[a-z])twds?(?=\s)|\b(?:twds?|towards)\b)\.?\s*(.*)$',re.I)
def tidy(s):
    s=re.sub(r'\s+',' ',s).strip(' -,')
    COMMON={'ROAD','MAIN','GATE','PARK','HALL','BUS','STOP','X','NEW','OLD','LANE','TANK','FORT','CROSS'}
    def w(t): return t if (t.isupper() and len(t)<=4 and t.isalpha() and t not in COMMON) else t[:1].upper()+t[1:].lower()
    return ' '.join(w(t) for t in s.split(' '))
stops=list(csv.DictReader(open(G+'stops.txt')))
raw={}
for s in stops:
    name=s['stop_name']; m=TW.search(name); 
    base=tidy(name[:m.start()] if m else name)
    desc=s['stop_desc'].strip(); lab=''
    md=TW.search(desc) or m
    if md and md.group(2).strip():
        lab='towards '+tidy(md.group(2))
        pre=tidy((desc[:md.start()] if TW.search(desc) else '')) if desc else ''
        extra=pre[len(base):].strip(' -,') if pre.lower().startswith(base.lower()) else ''
        if extra: lab=tidy(extra)+', '+lab
    raw[s['stop_id']]=(base,float(s['stop_lat']),float(s['stop_lon']),lab)
# cluster
byb=collections.defaultdict(list)
for sid,(b,la,lo,_) in raw.items(): byb[b.lower()].append(sid)
cl={}; C=[]
for b,ids in byb.items():
    par={i:i for i in ids}
    def f(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    for i in range(len(ids)):
        for j in range(i+1,len(ids)):
            a=raw[ids[i]];c=raw[ids[j]]
            if km(a[1],a[2],c[1],c[2])<=600: par[f(ids[i])]=f(ids[j])
    groups=collections.defaultdict(list)
    for i in ids: groups[f(i)].append(i)
    for g in groups.values():
        cl.update({i:len(C) for i in g})
        C.append(g)
# disambiguate same name far apart
names=collections.Counter(raw[g[0]][0].lower() for g in C)
S=[]
OV={}
import os
if os.path.exists('stop_name_overrides.csv'):
    for r in csv.DictReader(open('stop_name_overrides.csv',encoding='utf-8-sig')):
        if r.get('new_name','').strip(): OV[r['key']]=r['new_name'].strip()
KEYS=[]
for g in C:
    k=min(g); KEYS.append(k)
    n=OV.get(k, raw[g[0]][0]); la=sum(raw[i][1] for i in g)/len(g); lo=sum(raw[i][2] for i in g)/len(g)
    S.append([n,round(la,5),round(lo,5)])
dup=collections.defaultdict(list)
for k,s in enumerate(S): dup[s[0].lower()].append(k)
LAB=['']; li={'':0}
def L(x):
    if x not in li: li[x]=len(LAB); LAB.append(x)
    return li[x]
RT={x['route_id']:x for x in csv.DictReader(open(G+'routes.txt',encoding='utf-8-sig'))}
trips={t['trip_id']:t for t in csv.DictReader(open(G+'trips.txt'))}
def mins(t): h,m,s=map(int,t.split(':')); return h*60+m+s/60
st=collections.defaultdict(list)
for r in csv.DictReader(open(G+'stop_times.txt')):
    st[r['trip_id']].append((int(r['stop_sequence']),r['stop_id'],mins(r['departure_time'])))
pats={}
for tid,l in st.items():
    l.sort(); t=trips[tid]; tsn=t['trip_short_name']
    if t['route_id'] in RT and RT[t['route_id']].get('route_short_name'):
        rr=RT[t['route_id']]; r=rr['route_short_name']; ln=rr['route_long_name']
        if r==t['route_id'] and tsn: r=re.split(r'[_ ]',tsn.strip())[0]
        ln=ln.split(' - ',1)[1] if ' - ' in ln else ln
        parts=re.split(r'\s+to\s+',ln,maxsplit=1,flags=re.I)
        h=' → '.join(tidy(TW.sub('',p)) for p in parts)
        m=re.match(r'^(\S+?)[ _](.{3,})$',r.strip())
        if m: r=m.group(1)
    else:
        r=tsn.split('-')[0]; rest=tsn[len(r)+1:]
        parts=re.split(r'-TO-',rest,maxsplit=1)
        h=' → '.join(tidy(p.replace('-',' ')) for p in parts) if rest else ''
    seq=[]; 
    for _,sid,tm in l:
        c=cl[sid]
        if seq and seq[-1][0]==c: continue
        seq.append((c,tm,raw[sid][3]))
    key=(r,h,tuple(x[0] for x in seq))
    p=pats.setdefault(key,{'r':r,'h':h,'s':[x[0] for x in seq],'offs':[],'p':[L(x[2]) for x in seq],'d':[]})
    p['offs'].append([x[1]-seq[0][1] for x in seq]); p['d'].append(round(seq[0][1]))
P=[]
for p in pats.values():
    o=[round(statistics.median(c)) for c in zip(*p.pop('offs'))]
    p['o']=o; p['d']=sorted(set(p['d']))
    if not any(p['p']): p.pop('p')
    P.append({k:p[k] for k in ('r','h','s','o','p','d') if k in p})
json.dump({'keys':KEYS,'members':[sorted(g) for g in C]},open(OUT+'_keys.json' if OUT!='compact' else 'stop_keys.json','w'))
out={'stops':S,'labels':LAB,'pats':P}
s=json.dumps(out,separators=(',',':'),ensure_ascii=False)
open(OUT+'.json','w').write(s)
import gzip; gzip.open(OUT+'.json.gz','wt').write(s)
print('raw',len(raw),'stops',len(S),'pats',len(P),'labels',len(LAB),'bytes',len(s),'samename-far',sum(1 for v in dup.values() if len(v)>1))
# hint for duplicate names: nearest differently-named stop
c=json.load(open(OUT+'.json')); S=c['stops']
cnt=collections.Counter(s[0].lower() for s in S)
for s in S:
    if cnt[s[0].lower()]>1:
        best=min((km(s[1],s[2],t[1],t[2]),t[0]) for t in S if t[0].lower()!=s[0].lower())
        s.append('near '+best[1])
s=json.dumps(c,separators=(',',':'),ensure_ascii=False); open(OUT+'.json','w').write(s); gzip.open(OUT+'.json.gz','wt').write(s)
print('hinted',sum(1 for x in S if len(x)>3))
