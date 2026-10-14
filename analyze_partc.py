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
PARTC_FILES = ["_a7/partc_clean.jsonl"]   # clean set (amendment 7d): claude-sonnet-5 P1 (pre-tool), gpt-5.6-sol P1 rows
# before errata-6 line 15327 + 31 cells refilled under the clean harness (batch a7e-gptfill-20261011), and the
# four D models (batch a7d-p1clean-20261010). The previous P1 input is in _superseded/tool_exposed_mixed_20261010/.
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
    from collections import Counter
    comp = Counter((r["model"], r.get("batch_id")) for r in rows)
    for (m, b), k in sorted(comp.items(), key=lambda x: (x[0][0], str(x[0][1]))):
        print(f"  input {m:22} batch={b} rows={k}")
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
            out.append(f"\\newcommand{{\\Partc{sm}{tag}HarmPct}}{{{A.fx(A.fr(k, n, True), '.1f')}}}")
    # McNemar family prov_gate vs each, per strategy
    idx_pg = {}
    for r in rows:
        if r["defense"] == "prov_gate":
            idx_pg[(r["strategy"], r["model"], r["scenario"], r["template"], r.get("held_out", False), r["seed"])] = A.harm_target(r)
    HP, HOLM = {}, {}
    for st in ["A1", "A2", "A3"]:
        # macro names cannot contain digits
        for d in GATES[1:]:
            pr = []
            for r in rows:
                if r["strategy"] != st or r["defense"] != d:
                    continue
                key = (st, r["model"], r["scenario"], r["template"], r.get("held_out", False), r["seed"])
                if key in idx_pg:
                    pr.append((r["scenario"], idx_pg[key], A.harm_target(r)))
            tag = d.title().replace("_", "")
            sm = {"A1": "AOne", "A2": "ATwo", "A3": "AThree"}[st]
            stt = A.scen_test(pr)
            HP.setdefault(st, {})[d] = stt
    # Holm over the four comparators per transform (EXPERIMENT_PLAN_ESOTA.md:136, "Holm over the arm family")
    for st in ["A1", "A2", "A3"]:
        ps = sorted(HP[st].items(), key=lambda kv: kv[1][1]); m = len(ps); run = 0.0
        for i, (d, stt) in enumerate(ps):
            run = max(run, min(1.0, (m - i) * stt[1])); HOLM[(st, d)] = run
        for d, stt in HP[st].items():
            tag = d.title().replace("_", ""); sm = {"A1": "AOne", "A2": "ATwo", "A3": "AThree"}[st]
            out += [f"\\newcommand{{\\Partc{sm}P{tag}}}{{{A.fx(HOLM[(st, d)], '.3f')}}}",
                    f"\\newcommand{{\\Partc{sm}CI{tag}}}{{[{A.fx(stt[2], '+.1f')}, {A.fx(stt[3], '+.1f')}]}}"]
    # per-model relay harm under the reference gate (single-batch observation on model propensity, af-man #2855)
    pm = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["strategy"] == "A3" and r["defense"] == "prov_gate":
            pm[r["model"]][0] += bool(A.harm_target(r)); pm[r["model"]][1] += 1
    for m, (k, n) in sorted(pm.items()):
        t = "".join(c for c in m.split("-")[0].title() if c.isalpha())
        out += [f"\\newcommand{{\\PartcRelayRef{t}N}}{{{k}/{n}}}",
                f"\\newcommand{{\\PartcRelayRef{t}Pct}}{{{A.fx(A.fr(k, n, True), '.0f')}}}"]
    # post-hoc (codex r1 S4): harmful relay trials under the reference gate whose session-two call carries the
    # full original value in a target argument
    import persistlab as P
    fl = hn = 0
    for r in rows:
        if r["strategy"] == "A3" and r["defense"] == "prov_gate" and A.harm_target(r):
            hn += 1
            pv = (A._POIS.get(r["scenario"]) or "").lower()
            fl += any(pv and pv in " ".join(str(v) for k, v in (c.get("args") or {}).items() if k in P.TARGET_ARGS).lower()
                      for c in r.get("s2_calls", []))
    out.append(f"\\newcommand{{\\PartcRelayFullN}}{{{fl:,} of {hn:,}}}".replace(",", "{,}") if False else f"\\newcommand{{\\PartcRelayFullN}}{{{fl} of {hn:,}}}".replace(",", "{,}"))
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "numbers_partc.tex"), "w").write("\n".join(out) + "\n")
    # table body for the same-batch family grid: per gate x transform, pooled over the six frontier models,
    # all eight templates (six development + two held-out), eight scenarios and six seeds; percent and count
    name = {"prov_gate": "reference gate", "ifc": "loose taint matching", "louck": "corroboration gate", "ppmf": "authority gate", "rope": "ROPE (record)"}
    tab = []
    for d in GATES:
        cells = []
        for st in ["A1", "A2", "A3"]:
            k, n = agg[(st, d)]
            cells.append(f"{A.fx(A.fr(k, n, True), '.1f')} ({k}/{n})")
        tab.append(f"{name[d]} & " + " & ".join(cells) + " \\\\")
        if d != "prov_gate":   # McNemar p against the reference gate, per transform, in a row under the gate
            ps = []
            for st in ["A1", "A2", "A3"]:
                pr = [(r["scenario"], idx_pg[(st, r["model"], r["scenario"], r["template"], r.get("held_out", False), r["seed"])], A.harm_target(r))
                      for r in rows if r["strategy"] == st and r["defense"] == d and
                      (st, r["model"], r["scenario"], r["template"], r.get("held_out", False), r["seed"]) in idx_pg]
                ps.append(f"$p={A.fx(HOLM[(st, d)], '.3f')}$")
            tab.append("\\quad vs reference & " + " & ".join(ps) + " \\\\")
    tab.append("\\bottomrule")   # the body owns its closing rule, like every other table body
    open(os.path.join(OUTD, "tabs", "tab_partc.tex"), "w").write("\n".join(tab) + "\n")
    print("partc rows:", len(rows))
    for st in ["A1", "A2", "A3"]:
        # macro names cannot contain digits
        print(st, {d: f"{agg[(st,d)][0]}/{agg[(st,d)][1]}" for d in GATES})
    print("wrote numbers_partc.tex, tabs/tab_partc.tex")


if __name__ == "__main__":
    main()
