"""Delegated-benign runner (E-SOTA amendment 6): the value-renamed twin of the clean delegated document,
same 8 instructions as the attack grid, 7 arms, benign oracle. env: MODELS, ARMS (default
none,prov_gate,prov_strict,ifc,louck,ppmf,rope), NS (seeds, 10), SCEN (default all 8), OUT, BATCH_ID, WORKERS.
Dedup reads ONLY this OUT file (resume the same batch), like run_esota."""
import os, json, time
from concurrent.futures import ThreadPoolExecutor
import persistlab as P

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
MODELS = os.environ.get("MODELS", "claude-sonnet-5,gpt-5.6-sol,gemini-3.1-pro,deepseek-v4.1-flash,glm-5.3,kimi-k3").split(",")
ARMS = os.environ.get("ARMS", "none,prov_gate,prov_strict,ifc,louck,ppmf,rope").split(",")
NS = int(os.environ.get("NS", "10"))
SC = {s.key: s for s in P.delegated_scenarios()}
SCEN = os.environ.get("SCEN", ",".join(SC)).split(",")
BATCH_ID = os.environ.get("BATCH_ID", "deleg-" + time.strftime("%Y%m%d"))


def run_one(j):
    m, sk, d, s = j
    try:
        r = P.run_chain(m, SC[sk], defense=d, seed=s, benign=True, phase="delegated")
        r["phase"] = "delegated"
        r["batch_id"] = BATCH_ID
        return r
    except Exception as e:
        return {"phase": "delegated", "model": m, "scenario": sk, "defense": d, "seed": s, "error": str(e)[:140]}


if __name__ == "__main__":
    for m in MODELS:
        P.assert_served_root(m)
    out = os.environ.get("OUT", os.path.join(RES, "grid_delegated.jsonl"))
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                r = json.loads(l)
                if not r.get("error") and r.get("phase"):
                    done.add((r["phase"], r["model"], r["scenario"], r["defense"], r["seed"]))
            except Exception:
                pass
    todo = [(m, sk, d, s) for m in MODELS for sk in SCEN for d in ARMS for s in range(NS)
            if ("delegated", m, sk, d, s) not in done]
    print(f"{len(todo)} todo, {len(done)} done", flush=True)
    t0 = time.time()
    consec = 0
    with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("WORKERS", "6"))) as ex:
        for n, r in enumerate(ex.map(run_one, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush()
            consec = consec + 1 if (r.get("err") or r.get("error")) else 0
            if consec >= 20:
                print(f"CIRCUIT_BREAK DELEG: 20 consecutive err rows, stopping", flush=True)
                os._exit(3)
            if n % 100 == 0:
                print(n, "/", len(todo), round(time.time() - t0), "s", flush=True)
    print("DELEG_DONE", len(todo), round(time.time() - t0), "s", flush=True)
