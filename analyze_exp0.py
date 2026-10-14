"""Exp0 (amendments 7, 7b): does exposing the no-op lookup_directory tool change behavior? (a) delegated benign, no
defense, 80 cells per model, tool hidden vs exposed: preservation. (b) A3 relay under the reference gate, 3 models,
hidden vs exposed: harm (analyze.harm_target). Paired McNemar on (model, scenario, seed[, template]). Emits
numbers_exp0.tex + tabs/tab_exp0.tex. Inputs: results/_a7/exp0_*.jsonl."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "_a7")
DELEG = {"hidden": ["exp0_deleg_hidden.jsonl", "exp0_deleg_hidden_32b.jsonl"],
         "exposed": ["exp0_deleg_exposed.jsonl", "exp0_deleg_exposed_32b.jsonl"]}
RELAY = {"hidden": ["exp0_relay_hidden.jsonl"], "exposed": ["exp0_relay_exposed.jsonl"]}
SHORT = {"deepseek-v4.1-flash": "deepseek-v4.1", "glm-5.3": "glm-5.3", "kimi-k3": "kimi-k3",
         "qwen3-32b-local": "qwen3-32b"}


def load(files, outcome):
    d = {}
    for f in files:
        for l in open(os.path.join(RES, f)):
            r = json.loads(l)
            if r.get("err") or r.get("error") or not r.get("phase"):
                continue
            d[(r["model"], r["scenario"], r.get("template"), r.get("held_out", False), r["seed"])] = outcome(r)
    return d


def block(name, files, outcome, tag):
    h, e = load(files["hidden"], outcome), load(files["exposed"], outcome)
    rows, macros = [], []
    models = sorted({k[0] for k in h} & {k[0] for k in e})
    allp = []
    for m in models + ["pooled"]:
        ks = [k for k in h if k in e and (m == "pooled" or k[0] == m)]
        pairs = [(h[k], e[k]) for k in ks]
        trip = [(k[1], h[k], e[k]) for k in ks]
        allp = pairs
        kh, ke, n = sum(a for a, b in pairs), sum(b for a, b in pairs), len(pairs)
        p = A.scen_test(trip)[1]
        ps = "$<$0.001" if p < 0.001 else A.fx(p, ".3f")   # math-mode < so OT1 text encoding does not print an inverted mark
        lab = SHORT.get(m, m)
        rows.append(f"{name} & {lab} & {A.fx(A.fr(kh, n, True), '.1f')} ({kh}/{n}) & {A.fx(A.fr(ke, n, True), '.1f')} ({ke}/{n}) & "
                    f"{A.fx(A.fr(ke - kh, n, True), '+.1f')} & {ps} \\\\")
        t = "".join(c for c in lab.title() if c.isalpha())
        macros += [f"\\newcommand{{\\ExpZero{tag}{t}Hidden}}{{{A.fx(A.fr(kh, n, True), '.1f')}}}",
                   f"\\newcommand{{\\ExpZero{tag}{t}Exposed}}{{{A.fx(A.fr(ke, n, True), '.1f')}}}",
                   f"\\newcommand{{\\ExpZero{tag}{t}Diff}}{{{A.fx(A.fr(ke - kh, n, True), '+.1f')}}}",
                   f"\\newcommand{{\\ExpZero{tag}{t}P}}{{{ps}}}"]
    return rows, macros


def d_vs_p1():
    """Post-hoc (ra-01 #2824, af-man #2838): same-model cells of the clean batch against the archived mixed batch,
    for the three models in both (gemini-3.1-pro, deepseek-v4.1-flash, glm-5.3) x 3 strategies x 5 gates. The
    pre-registered effect threshold is 5 pp (amendment 7b D). Emits counts and the flagged cells."""
    root = os.path.dirname(RES)
    old_f = os.path.join(root, "archive", "tool_exposed_mixed_20261010", "grid_adaptive_pc_frontier.jsonl")
    new_f = os.path.join(RES, "a7d_p1clean.jsonl")
    M = {"gemini-3.1-pro", "deepseek-v4.1-flash", "glm-5.3"}
    def agg(f):
        a = defaultdict(lambda: [0, 0])
        for l in open(f):
            r = json.loads(l)
            if r.get("err") or r.get("error") or r.get("model") not in M:
                continue
            k = (r["model"], r["strategy"], r["defense"]); a[k][0] += bool(A.harm_target(r)); a[k][1] += 1
        return a
    o, n = agg(old_f), agg(new_f)
    diffs = {k: A.fr(n[k][0], n[k][1], True) - A.fr(o[k][0], o[k][1], True) for k in n if k in o}
    big = sorted((k for k, d in diffs.items() if abs(d) > 5), key=lambda k: diffs[k])
    rest = max(abs(d) for k, d in diffs.items() if k not in big)
    m = [f"\\newcommand{{\\DvPCells}}{{{len(diffs)}}}", f"\\newcommand{{\\DvPOver}}{{{len(big)}}}",
         f"\\newcommand{{\\DvPRestMax}}{{{A.fx(rest, '.1f')}}}"]
    names = {"prov_gate": "Ref", "ifc": "Ifc"}
    for k in big:
        t = names.get(k[2], k[2].title())
        m += [f"\\newcommand{{\\DvPGemini{t}Old}}{{{A.fx(A.fr(o[k][0], o[k][1], True), '.1f')}}}",
              f"\\newcommand{{\\DvPGemini{t}New}}{{{A.fx(A.fr(n[k][0], n[k][1], True), '.1f')}}}"]
        print("flag", k, A.fx(diffs[k], "+.1f"))
    return m


def main():
    r1, m1 = block("delegated", DELEG, lambda r: bool(r.get("preserved")), "Deleg")
    r2, m2 = block("relay", RELAY, lambda r: bool(A.harm_target(r)), "Relay")
    L = ["% auto: analyze_exp0.py", "\\begin{tabular}{@{}llcccc@{}}", "\\toprule",
         "condition & model & hidden & exposed & diff & p \\\\", "\\midrule"] + r1 + ["\\midrule"] + r2 + \
        ["\\bottomrule", "\\end{tabular}"]
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "tabs", "tab_exp0.tex"), "w").write("\n".join(L) + "\n")
    open(os.path.join(OUTD, "numbers_exp0.tex"), "w").write("\n".join(m1 + m2 + d_vs_p1()) + "\n")
    print("\n".join(r1 + r2))


if __name__ == "__main__":
    main()
