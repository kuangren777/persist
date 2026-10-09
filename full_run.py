"""Full data collection for the two-stage persistence paper.

Primary: contact-poisoning chain (session1 remembers an attacker-supplied contact from an untrusted
doc; session2 benign 'email Bob' uses it). Secondary: policy-CC chain. Plus the benign-preference
utility arm. 7 models x 4 defenses. Deterministic oracle. Writes jsonl under results/.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
import persistlab as P
from concurrent.futures import ThreadPoolExecutor

MODELS = ["claude-sonnet-5", "gpt-5.6-sol", "gemini-3.1-pro", "deepseek-v4.1-flash",
          "glm-5.3", "kimi-k3", "qwen3-8b-local"]
DEFENSES = ["none", "write_filter", "spotlight", "provenance"]
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(RES, exist_ok=True)

N_ATTACK = int(os.environ.get("N_ATTACK", "40"))     # seeds per (model,defense) for the primary chain
N_BENIGN = int(os.environ.get("N_BENIGN", "20"))
N_POLICY = int(os.environ.get("N_POLICY", "30"))     # secondary chain, none+provenance only


def jobs():
    J = []
    for m in MODELS:
        for d in DEFENSES:
            for s in range(N_ATTACK):
                J.append(("contact", m, d, s))
            for s in range(N_BENIGN):
                J.append(("benign", m, d, s))
        for d in ("none", "provenance"):
            for s in range(N_POLICY):
                J.append(("policy", m, d, s))
    return J


def run_one(j):
    kind, m, d, s = j
    try:
        if kind == "contact":
            r = P.run_chain(m, defense=d, seed=s, chain=P.contact_chain())
            return {"kind": kind, "model": m, "defense": d, "seed": s,
                    "persisted": r["persisted"], "activated": r["activated"], "blocked": r["blocked"],
                    "err": bool(r["s1_err"] or r["s2_err"])}
        if kind == "policy":
            r = P.run_chain(m, defense=d, seed=s, chain=P.default_chain())
            return {"kind": kind, "model": m, "defense": d, "seed": s,
                    "persisted": r["persisted"], "activated": r["activated"], "blocked": r["blocked"],
                    "err": bool(r["s1_err"] or r["s2_err"])}
        r = P.run_benign(m, defense=d, seed=s)
        return {"kind": kind, "model": m, "defense": d, "seed": s,
                "remembered": r["remembered"], "preserved": r["preserved"], "err": bool(r["s2_err"])}
    except Exception as e:
        return {"kind": kind, "model": m, "defense": d, "seed": s, "error": str(e)[:120]}


if __name__ == "__main__":
    out = os.path.join(RES, "full.jsonl")
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                r = json.loads(l)
                if not r.get("error"):
                    done.add((r["kind"], r["model"], r["defense"], r["seed"]))
            except Exception:
                pass
    todo = [j for j in jobs() if j not in done]
    print(f"{len(todo)} todo, {len(done)} done", flush=True)
    t0 = time.time()
    with open(out, "a") as f, ThreadPoolExecutor(10) as ex:
        for n, r in enumerate(ex.map(run_one, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush()
            if n % 50 == 0:
                print(n, "/", len(todo), round(time.time() - t0), "s", flush=True)
    print("ALL DONE", len(todo), round(time.time() - t0), "s", flush=True)
