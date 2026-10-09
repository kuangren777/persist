"""Part c (adaptive-per-gate, P1+P2+local) analysis. Emits per-arm x strategy harm (pooled over the six
frontier models, P1 batch), dev-worst per arm, and the McNemar family prov_gate-vs-each per strategy, as
macros for the RQ1 adaptive paragraph. The none baseline is cross-batch (old adaptive batch for the five
original models + P2 for the three new ones) and is reported absolute-only. Excludes err/error rows;
denominators are valid cells (34559 of 34560 for P1; the one missing kimi cell and the 32b cell are
documented in ANALYSIS_LOG)."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
PARTC_FILES = ["grid_adaptive_pc_frontier.jsonl"]   # explicit input set (P1 frontier batch)
GATES = ["prov_gate", "ifc", "louck", "ppmf", "rope"]


def main():
    rows = []
    for f in PARTC_FILES:
        for l in open(os.path.join(RES, f)):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if r.get("error") or r.get("err") or not r.get("phase"):
                continue
            rows.append(r)
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        k = (r["strategy"], r["defense"])
        agg[k][0] += bool(A.harm_target(r)); agg[k][1] += 1
    out = []
    for st in ["A1", "A2", "A3"]:
        # macro names cannot contain digits
        for d in GATES:
            k, n = agg[(st, d)]
            tag = d.title().replace("_", "")
            sm = {"A1": "AOne", "A2": "ATwo", "A3": "AThree"}[st]
            out.append(f"\\newcommand{{\\Partc{sm}{tag}HarmPct}}{{{100.0*k/n:.1f}}}")
    # McNemar family prov_gate vs each, per strategy
    idx_pg = {}
    for r in rows:
        if r["defense"] == "prov_gate":
            idx_pg[(r["strategy"], r["model"], r["scenario"], r["template"], r.get("held_out", False), r["seed"])] = A.harm_target(r)
    for st in ["A1", "A2", "A3"]:
        # macro names cannot contain digits
        for d in GATES[1:]:
            pr = []
            for r in rows:
                if r["strategy"] != st or r["defense"] != d:
                    continue
                key = (st, r["model"], r["scenario"], r["template"], r.get("held_out", False), r["seed"])
                if key in idx_pg:
                    pr.append((idx_pg[key], A.harm_target(r)))
            tag = d.title().replace("_", "")
            sm = {"A1": "AOne", "A2": "ATwo", "A3": "AThree"}[st]
            out.append(f"\\newcommand{{\\Partc{sm}P{tag}}}{{{A.mcnemar(pr):.3f}}}")
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "numbers_partc.tex"), "w").write("\n".join(out) + "\n")
    # table body for the same-batch family grid: per gate x transform, pooled over the six frontier models,
    # all eight templates (six development + two held-out), eight scenarios and six seeds; percent and count
    name = {"prov_gate": "reference gate", "ifc": "taint matching", "louck": "Louck", "ppmf": "PPMF", "rope": "ROPE"}
    tab = []
    for d in GATES:
        cells = []
        for st in ["A1", "A2", "A3"]:
            k, n = agg[(st, d)]
            cells.append(f"{100.0*k/n:.1f} ({k}/{n})")
        tab.append(f"{name[d]} & " + " & ".join(cells) + " \\\\")
    tab.append("\\bottomrule")   # the body owns its closing rule, like every other table body
    open(os.path.join(OUTD, "tabs", "tab_partc.tex"), "w").write("\n".join(tab) + "\n")
    print("partc rows:", len(rows))
    for st in ["A1", "A2", "A3"]:
        # macro names cannot contain digits
        print(st, {d: f"{agg[(st,d)][0]}/{agg[(st,d)][1]}" for d in GATES})
    print("wrote numbers_partc.tex, tabs/tab_partc.tex")


if __name__ == "__main__":
    main()
