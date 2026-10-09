"""Block A adaptive grid runner. Scale-agnostic: all dimensions come from env, so af1 sets them per the
PM-approved scale. Writes results/grid_adaptive_<...>.jsonl (one batch_id). served_root guard + keep-last
dedup across existing grid_adaptive*.jsonl, same as run_grid.

env: MODELS, ARMS (default none,prov_gate,prov_gate_wide,prov_strict), STRATS (A1,A2,A3), NA (seeds),
     SCEN (comma list of scenario keys; default all 8), NDEV (dev templates to run, default 6),
     NHELD (held-out templates, default 2), OUT, BATCH_ID, WORKERS.
"""
import os, json, glob, time
from concurrent.futures import ThreadPoolExecutor
import persistlab as P
import persistlab_adaptive as A

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
MODELS = os.environ.get("MODELS", "claude-sonnet-5,gpt-5.6-sol,gemini-3.1-pro,qwen3-8b-local,llama31-8b-local").split(",")
ARMS = os.environ.get("ARMS", "none,prov_gate,prov_gate_wide,prov_strict").split(",")
STRATS = os.environ.get("STRATS", "A1,A2,A3").split(",")
NA = int(os.environ.get("NA", "6"))
NDEV = int(os.environ.get("NDEV", "6"))
NHELD = int(os.environ.get("NHELD", "2"))
ALL_SC = {s.key: s for s in P.scenarios()}
SCEN = os.environ.get("SCEN", ",".join(ALL_SC)).split(",")

def jobs():
    for m in MODELS:
        for strat in STRATS:
            for held, n in [(False, NDEV), (True, NHELD)]:
                for t in range(n):
                    for sk in SCEN:
                        for d in ARMS:
                            for s in range(NA):
                                yield (m, strat, t, held, sk, d, s)

def run_one(j):
    m, strat, t, held, sk, d, s = j
    sc = ALL_SC[sk]
    try:
        if strat == "A3":
            r = A.run_adaptive3(m, sc, t, defense=d, seed=s, held=held)
        else:
            r = A.run_adaptive(m, sc, strat, t, defense=d, seed=s, held=held)
        return r
    except Exception as e:
        return {"phase": "adaptive", "model": m, "strategy": strat, "template": t, "held_out": held,
                "scenario": sk, "defense": d, "seed": s, "error": str(e)[:140]}

if __name__ == "__main__":
    for m in MODELS:
        P.assert_served_root(m)
    out = os.environ.get("OUT", os.path.join(RES, "grid_adaptive.jsonl"))
    # dedup against ONLY this OUT file (resume the same batch); never glob other files (e.g. the pilot),
    # whose rows are a different batch_id and must not suppress cells in this run.
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                r = json.loads(l)
                if not r.get("error") and r.get("phase"):
                    done.add((r["model"], r["strategy"], r["template"], r.get("held_out", False),
                              r["scenario"], r["defense"], r["seed"]))
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
                print(f"CIRCUIT_BREAK ADAPTIVE: 20 consecutive err rows, stopping", flush=True)
                os._exit(3)
            if n % 100 == 0:
                print(n, "/", len(todo), round(time.time() - t0), "s", flush=True)
    print("ADAPTIVE_DONE", len(todo), round(time.time() - t0), "s", flush=True)
