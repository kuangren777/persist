"""E-SOTA runner: the ifc arm plus its same-batch comparison arms (none, prov_gate, prov_strict) on the
RQ2 attack grid and the benign arm, so the harm and preservation comparisons are paired within one batch
(EXPERIMENT_PLAN_ESOTA.md + amendment 1). Env-parameterized like run_adaptive_grid: dedup reads ONLY the
OUT file (never globs other grids), served_root guard, batch_id per row.

env: MODELS, ARMS (default none,prov_gate,prov_strict,ifc), PHASES (attack,benign), NA (attack seeds, 12),
     NB (benign seeds, 20), SCEN (default all 8), OUT, BATCH_ID, WORKERS.
"""
import os, json, time
from concurrent.futures import ThreadPoolExecutor
import persistlab as P

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
MODELS = os.environ.get("MODELS", "claude-sonnet-5,gpt-5.6-sol,gemini-3.1-pro,deepseek-v4.1-flash,glm-5.3,kimi-k3,qwen3-8b-local,llama31-8b-local,qwen3-32b-local").split(",")
ARMS = os.environ.get("ARMS", "none,prov_gate,prov_strict,ifc").split(",")
PHASES = set(os.environ.get("PHASES", "attack,benign").split(","))
NA = int(os.environ.get("NA", "12"))
NB = int(os.environ.get("NB", "20"))
SC = {s.key: s for s in P.scenarios()}
BS = {s.key: s for s in P.benign_scenarios()}
SCEN = os.environ.get("SCEN", ",".join(SC)).split(",")
BATCH_ID = os.environ.get("BATCH_ID", "esota-" + time.strftime("%Y%m%d"))

def jobs():
    for m in MODELS:
        if "attack" in PHASES:
            for sk in SCEN:
                for d in ARMS:
                    for s in range(NA):
                        yield ("attack", m, sk, d, s)
        if "benign" in PHASES:
            for bk in BS:
                for d in ARMS:
                    for s in range(NB):
                        yield ("benign", m, bk, d, s)

def run_one(j):
    phase, m, sk, d, s = j
    try:
        if phase == "benign":
            r = P.run_chain(m, BS[sk], defense=d, seed=s, benign=True, phase=phase)
        else:
            r = P.run_chain(m, SC[sk], defense=d, seed=s, phase=phase)
        r["phase"] = phase
        r["batch_id"] = BATCH_ID
        return r
    except Exception as e:
        return {"phase": phase, "model": m, "scenario": sk, "defense": d, "seed": s, "error": str(e)[:140]}

if __name__ == "__main__":
    for m in MODELS:
        P.assert_served_root(m)
    out = os.environ.get("OUT", os.path.join(RES, "grid_esota.jsonl"))
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                r = json.loads(l)
                if not r.get("error") and r.get("phase"):
                    done.add((r["phase"], r["model"], r["scenario"], r["defense"], r["seed"]))
            except Exception:
                pass
    todo = [j for j in jobs() if j not in done]
    print(f"{len(todo)} todo, {len(done)} done", flush=True)
    t0 = time.time()
    consec = 0
    with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("WORKERS", "8"))) as ex:
        for n, r in enumerate(ex.map(run_one, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush()
            consec = consec + 1 if (r.get("err") or r.get("error")) else 0
            if consec >= 20:
                print(f"CIRCUIT_BREAK ESOTA: 20 consecutive err rows, stopping", flush=True)
                os._exit(3)
            if n % 100 == 0:
                print(n, "/", len(todo), round(time.time() - t0), "s", flush=True)
    print("ESOTA_DONE", len(todo), round(time.time() - t0), "s", flush=True)
