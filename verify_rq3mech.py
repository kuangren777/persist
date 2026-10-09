import sys,json,collections
sys.path.insert(0,".")
import persistlab as P
from concurrent.futures import ThreadPoolExecutor
from math import comb
MODELS=["claude-sonnet-5","gpt-5.6-sol","gemini-3.1-pro","deepseek-v4.1-flash","glm-5.3","kimi-k3","qwen3-8b-local"]
BS=P.benign_scenarios(); BK={b.key:b for b in BS}
ARMS=["none","provenance","prov_gate"]
jobs=[(m,b.key,s,d) for m in MODELS for b in BS for s in range(20) for d in ARMS]  # 7*3*20*3=1260
def one(j):
    m,k,s,d=j
    try:
        r=P.run_chain(m,BK[k],defense=d,seed=s,benign=True,phase="rq3mech")
        return (m,k,s,d,r.get("preserved",False),r.get("gate_blocked",0),r.get("err",False))
    except Exception: return (m,k,s,d,False,-1,True)
rows=[]
with ThreadPoolExecutor(8) as ex:
    rows=list(ex.map(one,jobs))
json.dump(rows,open("results/verify/rq3mech.json","w"))
def mcnemar(pairs):
    b01=sum(1 for a,b in pairs if (not a) and b); b10=sum(1 for a,b in pairs if a and (not b)); n=b01+b10
    if n==0: return 1.0,b10,b01
    k=min(b01,b10); return min(1.0,2*sum(comb(n,i) for i in range(k+1))/(2**n)),b10,b01
D=collections.defaultdict(dict); blk=collections.Counter()
for m,k,s,d,p,b,e in rows:
    if e: continue
    D[(m,k,s)][d]=p
    if b and b>0: blk[d]+=b
pres=collections.Counter(); n=collections.Counter()
for key,v in D.items():
    for d in ARMS:
        if d in v: n[d]+=1; pres[d]+=int(v[d])
print("preserved pooled:",{d:f'{pres[d]}/{n[d]}' for d in ARMS})
print("gate_blocked in benign:",dict(blk) or "ALL ZERO")
for a,b in [("none","provenance"),("none","prov_gate"),("prov_gate","provenance")]:
    pr=[(v[a],v[b]) for v in D.values() if a in v and b in v]
    p,b10,b01=mcnemar(pr); print(f"{a} vs {b}: b10={b10} b01={b01} p={p:.4f} n={len(pr)}")
