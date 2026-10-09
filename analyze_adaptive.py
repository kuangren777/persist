"""RQ4 adaptive analysis (Block A). Reads the five results/grid_adaptive_<model>.jsonl files in ADAPTIVE_FILES, applies the frozen aggregation
(per strategy+arm: MAX harm over the 6 dev templates = adversarial worst-case; the 2 held-out templates
reported separately), and emits tabs/tab_rq4adapt.tex + numbers_adaptive.tex macros into analyze.out_dir().

harm = analyze.harm_target (the attacker value reaching a target arg under _normv), the same metric as the
main grid; adaptive rows keep the base scenario key + full poison, so harm_target works unchanged.
backend is read from the row, else derived from model and served_root (qwen3-8b-yf or port 8034 -> vllm-0.19.1,
Llama or port 8023 -> vllm-0.8.5, else hub). backend is printed only; it enters no macro.
"""
import json, glob, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A   # harm_target, mcnemar, pct, wilson

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
# The Block A adaptive files the paper's RQ4 adaptive table was frozen on (5 models x 8 scenarios x 6 seeds =
# 240 trials per template). Listed explicitly: a glob over grid_adaptive_*.jsonl also matched the later part c
# batch (grid_adaptive_pc_*, analyzed by analyze_partc.py), which changed every cell of tab_rq4adapt.tex.
ADAPTIVE_FILES = ["grid_adaptive_claude-sonnet-5.jsonl", "grid_adaptive_gemini-3.1-pro.jsonl",
                  "grid_adaptive_gpt-5.6-sol.jsonl", "grid_adaptive_llama31-8b-local.jsonl",
                  "grid_adaptive_qwen3-8b-yf.jsonl"]
STRATS = ["A1", "A2", "A3"]
SMAP = {"A1": "AOne", "A2": "ATwo", "A3": "AThree"}  # letter-only macro names (LaTeX control seqs cannot contain digits)
ARMS = ["none", "prov_gate", "prov_gate_wide", "prov_strict"]
ARMLAB = {"none": "no defense", "prov_gate": "gate alone", "prov_gate_wide": "gate + wide", "prov_strict": "strict"}
MODELS = ["claude-sonnet-5", "gpt-5.6-sol", "gemini-3.1-pro", "qwen3-8b-local", "qwen3-8b-yf", "llama31-8b-local"]

def backend_of(r):
    if r.get("backend"):
        return r["backend"]
    sr = str(r.get("served_root", ""))
    if r.get("model") == "qwen3-8b-yf" or "8034" in sr:   # the second Qwen3-8B server (port 8034)
        return "vllm-0.19.1"
    if "Llama" in sr or "llama" in sr or "8023" in sr:
        return "vllm-0.8.5"
    return "hub"

def load():
    seen = {}
    for f in [os.path.join(RES, x) for x in ADAPTIVE_FILES]:
        for l in open(f):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("err") or r.get("error") or not r.get("phase"):
                continue
            r["activated"] = A.harm_target(r)
            r["backend"] = backend_of(r)
            k = (r["model"], r["strategy"], r.get("template"), r.get("held_out", False),
                 r["scenario"], r["defense"], r["seed"])
            seen[k] = r
    return list(seen.values())

def harm_rate(rows):
    return (sum(r["activated"] for r in rows), len(rows))

def main():
    rows = load()
    if not rows:
        print("no adaptive rows yet"); return
    by = defaultdict(list)
    for r in rows:
        by[(r["strategy"], r["defense"], bool(r.get("held_out")), r.get("template"))].append(r)
    # worst-of-dev per (strategy, arm): the dev template with the highest pooled harm
    L = ["% auto: analyze_adaptive.py", "\\begin{tabular}{lcccc}", "\\toprule",
         "strategy & " + " & ".join(ARMLAB[a] for a in ARMS) + " \\\\", "\\midrule"]
    macros = []
    for strat in STRATS:
        cells = []
        for arm in ARMS:
            devs = [by[(strat, arm, False, t)] for t in range(6)]
            devs = [d for d in devs if d]
            if not devs:
                cells.append("--"); continue
            kn = max(devs, key=lambda d: harm_rate(d)[0])   # worst dev template
            k, n = harm_rate(kn)
            cells.append(f"{k}/{n}")
            macros.append(f"\\newcommand{{\\Adapt{SMAP[strat]}{arm.title().replace('_','')}WorstN}}{{{k}/{n}}}")
        L.append(f"{strat} & " + " & ".join(cells) + " \\\\")
    L += ["\\bottomrule", "\\end{tabular}"]
    OUT = A.out_dir()
    open(os.path.join(OUT, "tabs", "tab_rq4adapt.tex"), "w").write("\n".join(L) + "\n")
    # held-out confirmation + coverage/backends, as macros + a console summary
    held_line = []
    for strat in STRATS:
        for arm in ["prov_gate", "prov_strict"]:
            hd = [r for t in range(2) for r in by[(strat, arm, True, t)]]
            if hd:
                k, n = harm_rate(hd)
                macros.append(f"\\newcommand{{\\Adapt{SMAP[strat]}{arm.title().replace('_','')}HeldN}}{{{k}/{n}}}")
                held_line.append(f"{strat}/{arm} held {k}/{n}")
    open(os.path.join(OUT, "numbers_adaptive.tex"), "w").write("\n".join(macros) + "\n")
    from collections import Counter
    cov = Counter((r["model"], r["strategy"]) for r in rows)
    print(f"adaptive rows: {len(rows)}; backends: {Counter(r['backend'] for r in rows)}")
    print("coverage (model,strategy -> rows):", dict(cov))
    print("held-out:", "; ".join(held_line))
    print(f"wrote tabs/tab_rq4adapt.tex + numbers_adaptive.tex into {OUT}")

if __name__ == "__main__":
    main()
