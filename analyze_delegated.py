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
# amendment 9 (ra-01 #3179/#3191): delegated rows rerun with call arguments logged for 8 models; kimi-k3 keeps its
# earlier row (arguments not logged, any-argument oracle), flagged in the table. (file, models or None = all)
A9 = os.path.join(os.path.dirname(RES), "_a9")
DELEG_FILES = [(os.path.join(A9, "a9a_deleg_frontier.jsonl"), None),
               (os.path.join(A9, "a9a_deleg_qwen3-8b-local.jsonl"), None),
               (os.path.join(A9, "a9a_deleg_qwen3-32b-local.jsonl"), None),
               (os.path.join(A9, "a9a_deleg_llama31-8b-local.jsonl"), None),
               (os.path.join(RES, "grid_delegated_frontier.jsonl"), {"kimi-k3"})]

OLD_FILES = [(os.path.join(RES, "grid_delegated_frontier.jsonl"), None),
             (os.path.join(RES, "grid_delegated_local_clean.jsonl"), None)]
_LOCAL = ["qwen3-8b-local", "qwen3-32b-local", "llama31-8b-local"]
if not all(os.path.exists(os.path.join(A9, f"a9a_deleg_{m}.jsonl")) and
           sum(1 for _ in open(os.path.join(A9, f"a9a_deleg_{m}.jsonl"))) >= 560 for m in _LOCAL):
    # the amendment-9 local reruns are incomplete: keep the previous complete clean set (any-argument oracle) so no
    # table mixes complete and partial cells; the a9 set replaces it once all three local models reach 560 rows
    print("analyze_delegated: a9 local rows incomplete -> using the previous clean set")
    DELEG_FILES = OLD_FILES


def pres(r):
    """Main oracle: the delegated value in a target argument (amendment 9) where arguments are logged; the earlier
    any-argument oracle for rows without logged arguments (kimi-k3)."""
    return bool(r.get("preserved_target")) if "s2_calls" in r else bool(r.get("preserved"))   # explicit input set
MODELS = A.MODELS
ARMS = ["none", "prov_gate", "prov_strict", "ifc", "louck", "ppmf", "rope"]
ARMLAB = {"none": "no defense", "prov_gate": "reference gate", "prov_strict": "strict variant",
          "ifc": "loose taint matching", "louck": "corroboration gate", "ppmf": "authority gate", "rope": "ROPE"}


def load():
    seen = {}
    for f, keep in DELEG_FILES:
        if not os.path.exists(f):
            continue
        for l in open(f):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("err") or r.get("error") or r.get("phase") != "delegated":
                continue
            if keep and r["model"] not in keep:
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
        pk = sum(pres(r) for r in rs)
        rk = sum(bool(r.get("remembered")) for r in rs)
        wr = sum(1 for r in rs if not r.get("remembered"))  # store never formed: rope = Lemma-1 write guard, others = model did not write
        stats[d] = (pk, rk, wr, n)
        def pct(k):
            return A.fx(A.fr(k, n, True), ".1f") if n else "--"
        # paired vs none
        rel = "--"
        if d != "none":
            pairs = []
            for (m, sc, dd, s), r in idx.items():
                if dd != d:
                    continue
                rn = idx.get((m, sc, "none", s))
                if rn is not None:
                    pairs.append((sc, pres(rn), pres(r)))
            if pairs:
                p = A.scen_test(pairs)[1]
                # gate minus none (a drop is negative), percentage points
                drop = A.fr(sum(b for _, a, b in pairs) - sum(a for _, a, b in pairs), len(pairs), True)
                pmax = max(pmax, p)
                rel = A.fx(drop, "+.1f")
        L.append(f"{ARMLAB[d]} & {pct(pk)} & {pct(rk)} & {pct(wr)} & {rel} \\\\")
        tag = d.title().replace("_", "")
        macros += [f"\\newcommand{{\\Deleg{tag}PresPct}}{{{pct(pk)}}}",
                   f"\\newcommand{{\\Deleg{tag}RemPct}}{{{pct(rk)}}}",
                   f"\\newcommand{{\\Deleg{tag}NotStoredPct}}{{{pct(wr)}}}",
                   f"\\newcommand{{\\Deleg{tag}N}}{{{pk}/{n}}}"]
    L += ["\\bottomrule", "\\end{tabular}"]
    # remembered range over the five gates that keep the write (RQ3 text), and Louck's frontier-only d (RQ4 formula)
    rems = [A.fr(stats[d][1], stats[d][3], True) for d in ("prov_gate", "prov_strict", "ifc", "louck", "ppmf") if d in stats]
    macros += [f"\\newcommand{{\\DelegRemMinPct}}{{{A.fx(min(rems), '.1f')}}}", f"\\newcommand{{\\DelegRemMaxPct}}{{{A.fx(max(rems), '.1f')}}}"]
    FR = {"claude-sonnet-5", "gpt-5.6-sol", "gemini-3.1-pro", "deepseek-v4.1-flash", "glm-5.3", "kimi-k3"}
    lf = [r for (m, sc, dd, s), r in idx.items() if dd == "louck" and m in FR]
    macros.append(f"\\newcommand{{\\DelegLouckFrontierPresPct}}{{{A.fx(A.fr(sum(pres(r) for r in lf), len(lf), True), '.1f')}}}")
    # anomalies: gate trials whose preserved oracle is met (appendix paragraph), by gate and model group
    LOCAL = {"qwen3-8b-local", "qwen3-32b-local", "llama31-8b-local"}
    an = [r for (m, sc, dd, s), r in idx.items() if dd != "none" and r.get("preserved")]   # any-argument, as before
    loc = [r for r in an if r["model"] in LOCAL]
    macros += [f"\\newcommand{{\\DelegAnomN}}{{{len(an)}}}",
               f"\\newcommand{{\\DelegAnomTotal}}{{{len(idx):,}}}".replace(",", "{,}"),
               f"\\newcommand{{\\DelegAnomLocal}}{{{len(loc)}}}",
               f"\\newcommand{{\\DelegAnomQwenThirtyTwo}}{{{sum(r['model'] == 'qwen3-32b-local' for r in an)}}}",
               f"\\newcommand{{\\DelegAnomLocalRefused}}{{{sum(bool(r.get('gate_blocked')) for r in loc)}}}",
               f"\\newcommand{{\\DelegAnomFrontier}}{{{len(an) - len(loc)}}}"]
    # amendment 9 classes, rows with logged arguments only: (a) value only in a non-target argument, (b) value in a
    # target argument after an earlier refused call, (c) value in a target argument with no refused call
    logged = [r for r in an if "s2_calls" in r]
    ca = sum(1 for r in logged if not r.get("preserved_target"))
    cb = sum(1 for r in logged if r.get("preserved_target") and r.get("gate_blocked"))
    cc = sum(1 for r in logged if r.get("preserved_target") and not r.get("gate_blocked"))
    if logged:   # only the amendment-9 set has logged arguments
        macros += [f"\\newcommand{{\\DelegAnomLogged}}{{{len(logged)}}}", f"\\newcommand{{\\DelegAnomClassA}}{{{ca}}}",
                   f"\\newcommand{{\\DelegAnomClassB}}{{{cb}}}", f"\\newcommand{{\\DelegAnomClassC}}{{{cc}}}"]
    print("anomaly classes (logged rows): a", ca, "b", cb, "c", cc, "of", len(logged))
    for g, t in (("louck", "Louck"), ("ppmf", "Ppmf"), ("ifc", "Ifc"), ("prov_gate", "ProvGate")):
        macros.append(f"\\newcommand{{\\DelegAnom{t}}}{{{sum(r['defense'] == g for r in an)}}}")
    print("anomalies", len(an), "local", len(loc), "local refused-before", sum(bool(r.get('gate_blocked')) for r in loc),
          "frontier", [(r["model"], r["defense"], bool(r.get("gate_blocked"))) for r in an if r["model"] not in LOCAL])
    macros.append(f"\\newcommand{{\\DelegPairedPMax}}{{{'below 0.001' if pmax < 0.001 else 'at most ' + A.fx(pmax, '.3f')}}}")
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "tabs", "tab_delegated.tex"), "w").write("\n".join(L) + "\n")
    open(os.path.join(OUTD, "numbers_delegated.tex"), "w").write("\n".join(macros) + "\n")
    print("delegated rows:", len(idx))
    for d, (pk, rk, wr, n) in stats.items():
        print(f"  {d:11} preserved {pk}/{n} remembered {rk}/{n} write-refused {wr}/{n}")
    print("wrote tabs/tab_delegated.tex + numbers_delegated.tex")


if __name__ == "__main__":
    main()
