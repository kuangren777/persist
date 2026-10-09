"""Unified, resumable data collection for the two-stage persistence paper. Writes results/grid.jsonl.

Phases (each is an independent experiment / arm):
  attack   : RQ1 (none arm = activation gap) + RQ2 (5 defenses interception). 8 scenarios x 7 models.
  benign   : RQ3 preservation. benign scenario x 7 models x 5 defenses.
  launder  : RQ4 laundering robustness. 8 scenarios x 7 models x {none, provenance}.
  ablation : RQ4 component ablation. 8 scenarios x 7 models x {prov_annotate, prov_gate} (naive).
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(__file__))
import persistlab as P
from concurrent.futures import ThreadPoolExecutor

MODELS = os.environ.get("MODELS", "claude-sonnet-5,gpt-5.6-sol,gemini-3.1-pro,deepseek-v4.1-flash,glm-5.3,kimi-k3,qwen3-8b-local").split(",")
ATTACK_DEF = ["none", "write_filter", "spotlight", "whitelist", "provenance"]
RES = os.path.dirname(__file__) + "/results"
os.makedirs(RES, exist_ok=True)
NA = int(os.environ.get("NA", "12"))     # attack seeds
NB = int(os.environ.get("NB", "20"))     # benign seeds
NL = int(os.environ.get("NL", "12"))     # launder / ablation seeds
PHASES = set(os.environ.get("PHASES", "attack,benign,launder,ablation").split(","))
SC = P.scenarios()
SC_L = P.scenarios(launder=True)
WIDE_DEF = ["none", "provenance", "prov_norm", "prov_wide", "prov_gate", "prov_gate_wide"]
WIDE_BEN_DEF = ["prov_norm", "prov_wide", "prov_gate", "prov_gate_wide"]


def jobs():
    J = []
    for m in MODELS:
        if "attack" in PHASES:
            for sc in SC:
                for d in ATTACK_DEF:
                    for s in range(NA):
                        J.append(("attack", m, sc.key, d, s))
        if "benign" in PHASES:
            for bsc in P.benign_scenarios():
                for d in ATTACK_DEF:
                    for s in range(NB):
                        J.append(("benign", m, bsc.key, d, s))
        if "launder" in PHASES:
            for sc in SC:
                for d in ("none", "provenance", "prov_gate"):
                    for s in range(NL):
                        J.append(("launder", m, sc.key, d, s))
        if "ablation" in PHASES:
            for sc in SC:
                for d in ("prov_annotate", "prov_gate"):
                    for s in range(NL):
                        J.append(("ablation", m, sc.key, d, s))
        if "wide" in PHASES:
            for sc in SC:                       # RQ5 attack arm: none / provenance / prov_wide
                for d in WIDE_DEF:
                    for s in range(NA):
                        J.append(("wide", m, sc.key, d, s))
            for bsc in P.benign_scenarios():     # RQ5 benign cost of the normalized and wide arms
                for d in WIDE_BEN_DEF:
                    for s in range(NB):
                        J.append(("wide_benign", m, bsc.key, d, s))
    return J


SCByKey = {s.key: s for s in SC}
SCLByKey = {s.key: s for s in SC_L}
BSByKey = {s.key: s for s in P.benign_scenarios()}


def run_one(j):
    phase, m, sckey, d, s = j
    try:
        if phase == "benign":
            r = P.run_chain(m, BSByKey[sckey], defense=d, seed=s, benign=True, phase=phase)
        elif phase == "launder":
            r = P.run_chain(m, SCLByKey[sckey], defense=d, seed=s, launder=True, phase=phase)
        elif phase == "wide_benign":
            r = P.run_chain(m, BSByKey[sckey], defense=d, seed=s, benign=True, phase=phase)
        elif phase == "wide":
            r = P.run_chain(m, SCByKey[sckey], defense=d, seed=s, phase=phase)
        else:
            r = P.run_chain(m, SCByKey[sckey], defense=d, seed=s, phase=phase)
        r["phase"] = phase
        return r
    except Exception as e:
        return {"phase": phase, "model": m, "scenario": sckey, "defense": d, "seed": s, "error": str(e)[:140]}


if __name__ == "__main__":
    for _m in MODELS:                         # served_root guard: never run a local model on a wrong/absent port
        P.assert_served_root(_m)
    out = os.environ.get("OUT", os.path.join(RES, "grid.jsonl"))
    import glob
    done = set()
    for gf in glob.glob(os.path.join(RES, "grid*.jsonl")):
        for l in open(gf):
            try:
                r = json.loads(l)
                if not r.get("error"):
                    done.add((r["phase"], r["model"], r["scenario"], r["defense"], r["seed"]))
            except Exception:
                pass
    todo = [j for j in jobs() if j not in done]
    print(f"{len(todo)} todo, {len(done)} done", flush=True)
    t0 = time.time()
    with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("WORKERS", "4"))) as ex:
        for n, r in enumerate(ex.map(run_one, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush()
            if n % 100 == 0:
                print(n, "/", len(todo), round(time.time() - t0), "s", flush=True)
    print("GRID_DONE", len(todo), round(time.time() - t0), "s", flush=True)
