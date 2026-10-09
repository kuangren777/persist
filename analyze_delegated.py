"""Delegated-benign analysis (amendment 6): preservation per arm on the delegated grid (same 8 instructions,
clean docs, legitimate new values), absolute and relative-to-none (paired McNemar per gate), plus the
remembered rate (session-1 write happened). For rope, remembered=False with preservation=False marks the
write-side Lemma-1 refusal (store never formed), reported separately from read-side refusals. Emits
tabs/tab_delegated.tex + numbers_delegated.tex macros into analyze.out_dir(). Input: DELEG_FILES in
results/_esota/."""
import json, glob, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "_esota")
DELEG_FILES = ["grid_delegated_frontier.jsonl", "grid_delegated_local.jsonl"]   # explicit input set
MODELS = A.MODELS
ARMS = ["none", "prov_gate", "prov_strict", "ifc", "louck", "ppmf", "rope"]
ARMLAB = {"none": "no defense", "prov_gate": "reference gate", "prov_strict": "strict variant",
          "ifc": "taint matching", "louck": "Louck", "ppmf": "PPMF", "rope": "ROPE"}


def load():
    seen = {}
    for f in [os.path.join(RES, x) for x in DELEG_FILES]:
        for l in open(f):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("err") or r.get("error") or r.get("phase") != "delegated":
                continue
            k = (r["model"], r["scenario"], r["defense"], r["seed"])
            seen[k] = r
    return seen


def main():
    rows = load()
    if not rows:
        print("no delegated rows yet"); return
    idx = {k: r for k, r in rows.items() if r["model"] in set(MODELS)}
    L = ["% auto: analyze_delegated.py", "\\begin{tabular}{lcccc}", "\\toprule",
         "gate & preserved $\\uparrow$ & remembered & not stored & rel.\\ none \\\\", "\\midrule"]
    macros = []
    stats = {}
    pmax = 0.0  # largest paired McNemar p over the gates, reported once in the caption
    for d in ARMS:
        rs = [r for (m, sc, dd, s), r in idx.items() if dd == d]
        if not rs:
            continue
        n = len(rs)
        pk = sum(bool(r.get("preserved")) for r in rs)
        rk = sum(bool(r.get("remembered")) for r in rs)
        wr = sum(1 for r in rs if not r.get("remembered"))  # store never formed: rope = Lemma-1 write guard, others = model did not write
        stats[d] = (pk, rk, wr, n)
        def pct(k):
            return f"{100.0*k/n:.1f}" if n else "--"
        # paired vs none
        rel = "--"
        if d != "none":
            pairs = []
            for (m, sc, dd, s), r in idx.items():
                if dd != d:
                    continue
                rn = idx.get((m, sc, "none", s))
                if rn is not None:
                    pairs.append((bool(rn.get("preserved")), bool(r.get("preserved"))))
            if pairs:
                p = A.mcnemar(pairs)
                # gate minus none (a drop is negative), percentage points
                drop = 100.0 * (sum(b for a, b in pairs) - sum(a for a, b in pairs)) / len(pairs)
                pmax = max(pmax, p)
                rel = f"{drop:+.1f}"
        L.append(f"{ARMLAB[d]} & {pct(pk)} & {pct(rk)} & {pct(wr)} & {rel} \\\\")
        tag = d.title().replace("_", "")
        macros += [f"\\newcommand{{\\Deleg{tag}PresPct}}{{{pct(pk)}}}",
                   f"\\newcommand{{\\Deleg{tag}RemPct}}{{{pct(rk)}}}",
                   f"\\newcommand{{\\Deleg{tag}NotStoredPct}}{{{pct(wr)}}}",
                   f"\\newcommand{{\\Deleg{tag}N}}{{{pk}/{n}}}"]
    L += ["\\bottomrule", "\\end{tabular}"]
    macros.append(f"\\newcommand{{\\DelegPairedPMax}}{{{'below 0.001' if pmax < 0.001 else f'at most {pmax:.3f}'}}}")
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "tabs", "tab_delegated.tex"), "w").write("\n".join(L) + "\n")
    open(os.path.join(OUTD, "numbers_delegated.tex"), "w").write("\n".join(macros) + "\n")
    print("delegated rows:", len(idx))
    for d, (pk, rk, wr, n) in stats.items():
        print(f"  {d:11} preserved {pk}/{n} remembered {rk}/{n} write-refused {wr}/{n}")
    print("wrote tabs/tab_delegated.tex + numbers_delegated.tex")


if __name__ == "__main__":
    main()
