"""E-SOTA head-to-head analysis. Reads the results/_esota/grid_esota_*.jsonl files listed in ESOTA_FILES (attack + benign, arms
none/prov_gate/prov_strict/ifc/louck/ppmf/rope over the 9 models) and emits the RQ2 head-to-head table:
per-gate harm (attack) and benign preservation, pooled over the nine included models with a frontier-only
number alongside, plus a per-gate decision-rule breakdown (what each gate keys on). Harm = analyze.harm_target
(same metric as the main grid). Writes tabs/tab_esota.tex + numbers_esota.tex into analyze.out_dir().
"""
import json, glob, os, sys, random
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A


def _holm(pairs):
    """Holm step-down adjusted p-values; pairs is [(key, p), ...]. Returns {key: p_adj}."""
    order = sorted(range(len(pairs)), key=lambda i: pairs[i][1])
    k = len(pairs); adj = {}; running = 0.0
    for rank, i in enumerate(order):
        running = min(1.0, max(running, (k - rank) * pairs[i][1]))
        adj[pairs[i][0]] = running
    return adj


def _sig_macros(rows, ours="prov_gate", comps=("louck", "ppmf", "ifc", "rope"), B=2000):
    """Paired McNemar (exact, Holm over the comparison family) and paired-difference cluster-bootstrap 95% CI
    (clusters = (model, scenario)) for our gate vs each comparator, on harm (attack) and preservation (benign).
    Emits macros so every p-value and CI in the prose is generated, not hand-written (af-man #572/#585). The
    paired difference is ours-minus-other in percentage points; a p=1.00 is reported as no significant
    difference with its CI, never as equivalence (no pre-registered margin)."""
    random.seed(12345)
    MOD = set(A.MODELS)
    idx = {}
    for r in rows:
        if r["model"] in MOD:
            idx[(r["phase"], r["model"], r["scenario"], r["defense"], r["seed"])] = r
    def oc(r):
        return 1 if (r.get("activated") if r["phase"] == "attack" else r.get("preserved")) else 0
    out = []
    for phase, tag in (("attack", "Harm"), ("benign", "Pres")):
        pvals = []
        per = {}
        for b in comps:
            cl = defaultdict(list)
            mcp = []
            for (ph, m, sc, d, s), r in idx.items():
                if ph != phase or d != ours:
                    continue
                rb = idx.get((ph, m, sc, b, s))
                if rb is None:
                    continue
                a, bo = oc(r), oc(rb)
                cl[(m, sc)].append((a, bo)); mcp.append((bool(a), bool(bo)))
            p = A.mcnemar(mcp)
            keys = list(cl)
            def md(sample):
                ao = bb = n = 0
                for kk in sample:
                    for a, bo in cl[kk]:
                        ao += a; bb += bo; n += 1
                return 100.0 * (ao - bb) / n if n else 0.0
            point = md(keys)
            boots = sorted(md([random.choice(keys) for _ in keys]) for _ in range(B))
            lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B)]
            per[b] = (p, point, lo, hi)
            pvals.append((b, p))
        adj = _holm(pvals)
        widths = [max(abs(per[b][2]), abs(per[b][3])) for b in comps]
        for b in comps:
            p, point, lo, hi = per[b]
            bt = b.title()
            out += [f"\\newcommand{{\\Esota{tag}P{bt}}}{{{p:.2f}}}",
                    f"\\newcommand{{\\Esota{tag}PHolm{bt}}}{{{adj[b]:.2f}}}",
                    f"\\newcommand{{\\Esota{tag}Diff{bt}}}{{{point:+.2f}}}",
                    f"\\newcommand{{\\Esota{tag}CI{bt}}}{{[{lo:+.2f}, {hi:+.2f}]}}"]
        # preservation spread across the arm family (max-min, pp) for the intro/abstract.
        # NOTE: the outer loop variable is `phase`; `ph` is shadowed by the row loop above.
        if phase == "benign":
            pres = {}
            for d2 in ARMS:
                rs2 = [r for r in rows if r["phase"] == "benign" and r["defense"] == d2 and r["model"] in set(A.MODELS)]
                if rs2:
                    pres[d2] = 100.0 * sum(bool(r.get("preserved")) for r in rs2) / len(rs2)
            if pres:
                out.append(f"\\newcommand{{\\EsotaPresSpreadPp}}{{{max(pres.values())-min(pres.values()):.1f}}}")
        # family CI half-width bound over the no-difference comparators (louck, ppmf) for the summary sentence
        nd = [b for b in comps if b in ("louck", "ppmf")]
        bound = max(max(abs(per[b][2]), abs(per[b][3])) for b in nd) if nd else 0.0
        out.append(f"\\newcommand{{\\Esota{tag}NDCIbound}}{{{bound:.1f}}}")
    return out

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "_esota")
# explicit input set (the 9-model head-to-head; the rope arm comes from the two ropererun files after the
# rope_adapter fixes, pre-fix rope rows are in _esota/_superseded/). No cell key repeats across these files.
ESOTA_FILES = ["grid_esota_frontier.jsonl", "grid_esota_local.jsonl", "grid_esota_qwen8b.jsonl",
               "grid_esota_ropererun_frontier.jsonl", "grid_esota_ropererun_local.jsonl"]
MODELS = A.MODELS                 # the 9 included models
FRONTIER = A.FRONTIER             # the 6 gateway models
ARMS = ["none", "prov_gate", "prov_strict", "ifc", "louck", "ppmf", "rope", "rope_raw"]
ARMLAB = {"none": "no defense", "prov_gate": "reference gate", "prov_strict": "strict variant",
          "ifc": "taint matching", "louck": "Louck", "ppmf": "PPMF", "rope": "ROPE (memory-as-record)",
          "rope_raw": "ROPE (as-is)"}
# one-line decision rule per gate, for the difference table (PM: show ifc is not our method relabeled)
RULE = {"prov_gate": "refuse a target value that matches an untrusted-only stored item exactly",
        "prov_strict": "allow only a value that appears in user-sourced text (deny-by-default)",
        "ifc": "refuse a value whose normalized form appears in any untrusted input (value-level taint matching)",
        "louck": "allow unless value derives from untrusted memory without fresh user auth (channel origin)",
        "ppmf": "refuse a high-risk action whose value is backed only by untrusted-authority memory",
        "rope": "official ROPE, store read as the user's record, plus a structural write guard",
        "rope_raw": "official ROPE as-is, store read as untrusted input, no write guard"}

def load():
    seen = {}
    for f in [os.path.join(RES, x) for x in ESOTA_FILES]:
        for l in open(f):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("err") or r.get("error") or not r.get("phase"):
                continue
            if r.get("phase") in ("attack",):
                r["activated"] = A.harm_target(r)
            k = (r["phase"], r["model"], r["scenario"], r["defense"], r["seed"])
            seen[k] = r
    return list(seen.values())

def rate(rows, field):
    rows = [r for r in rows if r.get(field) is not None or field == "activated"]
    if not rows:
        return None
    return sum(bool(r.get(field)) for r in rows), len(rows)

def main():
    rows = load()
    if not rows:
        print("no esota rows yet"); return
    atk = [r for r in rows if r["phase"] == "attack"]
    ben = [r for r in rows if r["phase"] == "benign"]
    def pooled(phase_rows, defense, field, models):
        rs = [r for r in phase_rows if r["defense"] == defense and r["model"] in models]
        return (sum(bool(r.get(field)) for r in rs), len(rs)) if rs else (0, 0)
    L = ["% auto: analyze_esota.py", "\\begin{tabular}{@{}lp{4.4cm}cccc@{}}", "\\toprule",
         "gate & rule & harm (9) $\\downarrow$ & harm (frontier) $\\downarrow$ & preserve (9) $\\uparrow$ & preserve (frontier) $\\uparrow$ \\\\", "\\midrule"]
    macros = []
    for d in ARMS:
        hk, hn = pooled(atk, d, "activated", MODELS); fhk, fhn = pooled(atk, d, "activated", FRONTIER)
        pk, pn = pooled(ben, d, "preserved", MODELS); fpk, fpn = pooled(ben, d, "preserved", FRONTIER)
        if hn == 0 and pn == 0:
            continue
        def pct(k, n):
            return f"{100.0*k/n:.1f}" if n else "--"
        L.append(f"{ARMLAB[d]} & {RULE.get(d,'')} & {pct(hk,hn)} & {pct(fhk,fhn)} & {pct(pk,pn)} & {pct(fpk,fpn)} \\\\")
        tag = d.title().replace("_", "")
        macros += [f"\\newcommand{{\\Esota{tag}HarmPct}}{{{pct(hk,hn)}}}",
                   f"\\newcommand{{\\Esota{tag}PresPct}}{{{pct(pk,pn)}}}",
                   f"\\newcommand{{\\Esota{tag}HarmN}}{{{hk}/{hn}}}"]
    L += ["\\bottomrule", "\\end{tabular}"]
    OUTD = A.out_dir()
    macros += _sig_macros(rows)
    open(os.path.join(OUTD, "tabs", "tab_esota.tex"), "w").write("\n".join(L) + "\n")
    open(os.path.join(OUTD, "numbers_esota.tex"), "w").write("\n".join(macros) + "\n")
    from collections import Counter
    cov = Counter((r["phase"], r["model"], r["defense"]) for r in rows)
    print(f"esota rows: {len(rows)}; arms present: {sorted(set(r['defense'] for r in rows))}")
    print("coverage cells (phase,model,defense):", len(cov), "/", 2 * len(MODELS) * len(ARMS))
    for d in ARMS:
        hk, hn = pooled(atk, d, "activated", MODELS); pk, pn = pooled(ben, d, "preserved", MODELS)
        if hn or pn:
            print(f"  {d:11} harm {hk}/{hn}  preserve {pk}/{pn}")
    print("wrote tabs/tab_esota.tex + numbers_esota.tex")

if __name__ == "__main__":
    main()
