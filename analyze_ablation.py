"""Matching ablation (amendments 7, 7b, 7c option C). The reference gate with only the matching rule changed: exact
membership (prov_gate), raw lowercase containment (prov_gate_sub), normalized containment (prov_gate_norm) and
normalized containment on the raw target-argument strings (prov_gate_rawcall). Recognizer, prompt and refusal text are
identical across the four arms. Three models (claude-sonnet-5, gemini-3.1-pro, deepseek-v4.1-flash) x A1/A2/A3 x 8
templates x 8 scenarios x 3 seeds = 576 trials per model per arm. Harm = analyze.harm_target. Paired McNemar within
(model, strategy, template, held_out, scenario, seed). Emits numbers_ablation.tex + tabs/tab_ablation.tex.
Input: results/_a7/a7c_ablation.jsonl (batch a7c-ablation-20261010)."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
ABL_FILE = os.path.join(RES, "_a7", "a7c_ablation.jsonl")
ARMS = ["prov_gate", "prov_gate_sub", "prov_gate_norm", "prov_gate_rawcall"]
TAG = {"prov_gate": "Exact", "prov_gate_sub": "Sub", "prov_gate_norm": "Norm", "prov_gate_rawcall": "Rawcall"}
LAB = {"prov_gate": "exact membership", "prov_gate_sub": "raw containment",
       "prov_gate_norm": "normalized containment", "prov_gate_rawcall": "normalized, raw call strings"}
SM = {"A1": "AOne", "A2": "ATwo", "A3": "AThree"}
# only the pre-registered comparisons (amendments 7/7b): relay A3 confirmation (norm and sub vs exact) and the
# containment-vs-normalization contrast; encode A2 thresholds (norm vs exact, rawcall vs norm). Split A1 has none.
PAIRS = {"A1": [],
         "A2": [("prov_gate_norm", "prov_gate"), ("prov_gate_rawcall", "prov_gate_norm")],
         "A3": [("prov_gate_sub", "prov_gate"), ("prov_gate_norm", "prov_gate"), ("prov_gate_sub", "prov_gate_norm")]}


def load():
    idx = {}
    for l in open(ABL_FILE):
        r = json.loads(l)
        if r.get("err") or r.get("error") or not r.get("phase"):
            continue
        idx[(r["model"], r["strategy"], r.get("template"), r.get("held_out", False), r["scenario"],
             r["defense"], r["seed"])] = bool(A.harm_target(r))
    return idx


def fmt_p(p):
    return "below 0.001" if p < 0.001 else A.fx(p, ".3f")


def main():
    idx = load()
    agg = defaultdict(lambda: [0, 0])
    for (m, st, t, h, sc, d, s), v in idx.items():
        agg[(st, d)][0] += v; agg[(st, d)][1] += 1
    macros, L = [], ["% auto: analyze_ablation.py", "\\begin{tabular}{@{}lccc@{}}", "\\toprule",
                     "matching rule & split $\\downarrow$ & encode $\\downarrow$ & relay $\\downarrow$ \\\\", "\\midrule"]
    for d in ARMS:
        cells = []
        for st in ["A1", "A2", "A3"]:
            k, n = agg[(st, d)]
            cells.append(f"{A.fx(A.fr(k, n, True), '.1f')} ({k}/{n})")
            macros += [f"\\newcommand{{\\Abl{SM[st]}{TAG[d]}Pct}}{{{A.fx(A.fr(k, n, True), '.1f')}}}",
                       f"\\newcommand{{\\Abl{SM[st]}{TAG[d]}N}}{{{k}/{n}}}"]
        L.append(f"{LAB[d]} & " + " & ".join(cells) + " \\\\")
    L += ["\\bottomrule", "\\end{tabular}"]
    RAWP = {}
    for st in ["A1", "A2", "A3"]:
        for a, b in PAIRS[st]:
            pairs = []
            for (m, s2, t, h, sc, d, s), v in idx.items():
                if s2 != st or d != a:
                    continue
                w = idx.get((m, s2, t, h, sc, b, s))
                if w is not None:
                    pairs.append((sc, v, w))
            RAWP[(st, a, b)] = A.scen_test(pairs)[1]
    # Holm families as pre-registered (EXPERIMENT_PLAN_ESOTA.md:489 A3 "Holm over the two contrasts against prov_gate";
    # :531 A2 thresholds Holm over its two contrasts); the A3 containment-vs-normalization contrast stays uncorrected
    FAM = {"A2": [k for k in RAWP if k[0] == "A2"], "A3": [k for k in RAWP if k[0] == "A3" and k[2] == "prov_gate"]}
    ADJ = dict(RAWP)
    for st, ks in FAM.items():
        srt = sorted(ks, key=lambda k: RAWP[k]); run = 0.0
        for i, k in enumerate(srt):
            run = max(run, min(1.0, (len(srt) - i) * RAWP[k])); ADJ[k] = run
    ag = {k: v for k, v in agg.items()}
    ex = ag[("A3", "prov_gate")][0]
    for d in ("prov_gate_sub", "prov_gate_norm"):
        macros.append(f"\\newcommand{{\\AblAThree{TAG[d]}ClosedPct}}{{{A.fx(100 - A.fr(ag[('A3', d)][0], ex, True), '.0f')}}}")
    sn = []
    for (m, s2, t, h, sc, d, s), v in idx.items():
        if s2 == "A3" and d == "prov_gate_norm" and (m, s2, t, h, sc, "prov_gate_sub", s) in idx:
            sn.append((sc, v, idx[(m, s2, t, h, sc, "prov_gate_sub", s)]))
    _W = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
    macros.append(f"\\newcommand{{\\AblSubNormScenN}}{{{_W.get(A.scen_test(sn)[5], A.scen_test(sn)[5])}}}")
    for (st, a, b), p in ADJ.items():
        macros.append(f"\\newcommand{{\\Abl{SM[st]}P{TAG[a]}V{TAG[b]}}}{{{fmt_p(p)}}}")
        print(f"{st} {a} vs {b}: p={p:.3g} (raw {RAWP[(st, a, b)]:.3g})")
    # post-hoc (ra-01 #3172): relay pairs that normalized containment passed and raw containment refused, and how many
    # of them are admin grants (the stored marker fragment shrinks below the six-character floor after _normv)
    nd = [k for k, v in idx.items() if k[1] == "A3" and k[5] == "prov_gate_norm" and v
          and idx.get(k[:5] + ("prov_gate_sub",) + k[6:]) is False]
    macros += [f"\\newcommand{{\\AblNormOnlyN}}{{{len(nd)}}}",
               f"\\newcommand{{\\AblNormOnlyAdmin}}{{{sum(k[4] == 'add_admin' for k in nd)}}}"]
    print("norm-harm/sub-safe relay pairs:", len(nd), "admin:", sum(k[4] == "add_admin" for k in nd))
    # amendment 9b: benign cost of containment (user-authored arm, any-argument oracle; delegated arm, target oracle)
    b9 = os.path.join(RES, "_a9", "a9b_benign_abl.jsonl")
    if os.path.exists(b9):
        bi = {}
        for l in open(b9):
            r = json.loads(l)
            if not (r.get("error") or r.get("err")):
                bi[(r["model"], r["scenario"], r["seed"], r["defense"])] = bool(r.get("preserved"))
        for d in ("prov_gate", "prov_gate_sub", "prov_gate_norm"):
            v = [x for k, x in bi.items() if k[3] == d]
            macros.append(f"\\newcommand{{\\AblBenign{TAG[d]}N}}{{{sum(v)}/{len(v)}}}")
        for d in ("prov_gate_sub", "prov_gate_norm"):
            pr = [(k[1], bi[k[:3] + ("prov_gate",)], x) for k, x in bi.items() if k[3] == d and k[:3] + ("prov_gate",) in bi]
            macros.append(f"\\newcommand{{\\AblBenignP{TAG[d]}}}{{{A.fx(A.scen_test(pr)[1], '.2f')}}}")
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "tabs", "tab_ablation.tex"), "w").write("\n".join(L) + "\n")
    open(os.path.join(OUTD, "numbers_ablation.tex"), "w").write("\n".join(macros) + "\n")
    for st in ["A1", "A2", "A3"]:
        print(st, {d: f"{agg[(st, d)][0]}/{agg[(st, d)][1]}" for d in ARMS})
    print("wrote tabs/tab_ablation.tex + numbers_ablation.tex")


if __name__ == "__main__":
    main()
