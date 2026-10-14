"""Part d (amendment 5/5b, two-principal corroboration) analysis. Emits, per arm, the delegated preservation
under directory corroboration (benign x corr), the preservation under directory contradiction (benign x
contra, oracle = acting on the directory value) and the harm on attack x contra (analyze.harm_target), as
macros for RQ4 and a table body. ROPE rows are the errata-5c post-fix rerun (batch
partd-rope-prefixfix-20261008); pre-fix rows live in results/_superseded/. Excludes err rows; denominators
are valid cells. Six frontier models, eight scenarios, six seeds; no ifc or prov_strict arm (amendment 5).
CONTRA SCOPE: part d amendment 6 (ANALYSIS_LOG 2026-10-09, prereg 03ca66e95) fixed run_partd.DIR_CONTRA, which
had equalled the delegated notice's new value in 7 of 8 scenarios. The contra cells of those 7 scenarios were
rerun (batch partd-contrafix-20261009; defective rows in results/_superseded/partd_contra_defect_20261009/), so
benign x contra and attack x contra are genuine contradictions in all 8 scenarios and are pooled over all 8.
The earlier post-hoc payment_account-only restriction is removed."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
PARTD_FILES = ["grid_partd.jsonl"]   # explicit input set
ARMS = ["none", "prov_gate", "louck", "ppmf", "rope"]
TAG = {"none": "None", "prov_gate": "ProvGate", "louck": "Louck", "ppmf": "Ppmf", "rope": "Rope"}
NAME = {"none": "no defense", "prov_gate": "reference gate", "louck": "corroboration gate", "ppmf": "authority gate", "rope": "ROPE (record)"}
PHASES = {"partd_benign_corr": "Corr", "partd_benign_contra": "Contra", "partd_attack_contra": "Atk"}


def load():
    rows = []
    for f in PARTD_FILES:
        for l in open(os.path.join(RES, f)):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if r.get("err") or r.get("error") or r.get("phase") not in PHASES:
                continue
            rows.append(r)
    return rows


def outcome(r):
    return bool(A.harm_target(r)) if r["phase"] == "partd_attack_contra" else bool(r.get("preserved"))


def aggregate(rows):
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        k = (r["phase"], r["defense"])
        agg[k][0] += outcome(r)
        agg[k][1] += 1
    return agg


def pct(k, n):
    return A.fx(A.fr(k, n, True), ".1f") if n else "0.0"


def main():
    rows = load()
    agg = aggregate(rows)
    out = []
    for ph, pt in PHASES.items():
        for d in ARMS:
            k, n = agg[(ph, d)]
            out.append(f"\\newcommand{{\\Partd{pt}{TAG[d]}N}}{{{k}/{n}}}")
            out.append(f"\\newcommand{{\\Partd{pt}{TAG[d]}Pct}}{{{pct(k, n)}}}")
    # corroboration cell split (debate verdicts #1988/#1991): elevation = the session-one note was stored and the
    # session-two call carrying the value was allowed on the directory's authority; bypass = the note was never
    # stored, so the agent took the value from the directory answer and no stored item was involved.
    corr = [r for r in rows if r["phase"] == "partd_benign_corr"]
    split = {}
    for d in ARMS:
        rs = [r for r in corr if r["defense"] == d]
        el = sum(1 for r in rs if r.get("preserved") and r.get("remembered"))
        by = sum(1 for r in rs if r.get("preserved") and not r.get("remembered"))
        split[d] = (el, by, len(rs))
        out += [f"\\newcommand{{\\PartdElev{TAG[d]}N}}{{{el}/{len(rs)}}}",
                f"\\newcommand{{\\PartdElev{TAG[d]}Pct}}{{{pct(el, len(rs))}}}",
                f"\\newcommand{{\\PartdBypass{TAG[d]}N}}{{{by}/{len(rs)}}}",
                f"\\newcommand{{\\PartdBypass{TAG[d]}Pct}}{{{pct(by, len(rs))}}}"]
    SCN = {"recipient_replace": "recipient replacement", "cc_exfil": "carbon-copy exfiltration",
           "webhook_exfil": "webhook exfiltration", "payment_account": "payment-account change", "add_admin": "admin grant",
           "forwarding_rule": "mail-forwarding change", "dependency_url": "dependency-source change",
           "scheduled_task": "scheduled-report redirect"}
    ps = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in corr:
        if r["defense"] in ("louck", "ppmf"):
            ps[r["scenario"]][r["defense"]][0] += bool(r.get("preserved") and r.get("remembered"))
            ps[r["scenario"]][r["defense"]][1] += 1
    TS = ["% auto: analyze_partd.py, per-scenario elevation (post-hoc split)", "\\begin{tabular}{@{}lcc@{}}", "\\toprule",
          "scenario & corroboration gate $\\uparrow$ & authority gate $\\uparrow$ \\\\", "\\midrule"]
    for sc in SCN:
        a, b = ps[sc]["louck"], ps[sc]["ppmf"]
        TS.append(f"{SCN[sc]} & {A.fx(A.fr(a[0], a[1], True), '.0f')} ({a[0]}/{a[1]}) & {A.fx(A.fr(b[0], b[1], True), '.0f')} ({b[0]}/{b[1]}) \\\\")
    TS += ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(A.out_dir(), "tabs", "tab_partd_scen.tex"), "w").write("\n".join(TS) + "\n")
    # observational split (ra-01 #3805): preserved among trials where the model stored the note vs did not; the model
    # chose whether to store, so this is descriptive, not a causal effect of the note (P1 measures that)
    for d in ARMS:
        rs = [r for r in corr if r["defense"] == d]
        st = [r for r in rs if r.get("remembered")]; ns = [r for r in rs if not r.get("remembered")]
        for lab, grp in (("Stored", st), ("NotStored", ns)):
            k = sum(bool(r.get("preserved")) for r in grp)
            out += [f"\\newcommand{{\\Partd{lab}Pres{TAG[d]}N}}{{{k}/{len(grp)}}}",
                    f"\\newcommand{{\\Partd{lab}Pres{TAG[d]}Pct}}{{{pct(k, len(grp))}}}"]
    # per-scenario elevation range, the sensitivity of recovery to which value classes the platform records
    for d in ("louck", "ppmf"):
        per = defaultdict(lambda: [0, 0])
        for r in corr:
            if r["defense"] == d:
                per[r["scenario"]][0] += bool(r.get("preserved") and r.get("remembered"))
                per[r["scenario"]][1] += 1
        rates = {sc: A.fr(k, n, True) for sc, (k, n) in per.items() if n}
        lo, hi = min(rates.values()), max(rates.values())
        out += [f"\\newcommand{{\\PartdElevMin{TAG[d]}Pct}}{{{A.fx(lo, '.0f')}}}",
                f"\\newcommand{{\\PartdElevMax{TAG[d]}Pct}}{{{A.fx(hi, '.0f')}}}"]
        print(d, "per-scenario elevation", {k: A.fx(v, ".0f") for k, v in sorted(rates.items())})
    models = sorted({r["model"] for r in rows})
    out.append(f"\\newcommand{{\\PartdNModels}}{{{len(models)}}}")
    OUTD = A.out_dir()
    open(os.path.join(OUTD, "numbers_partd.tex"), "w").write("\n".join(out) + "\n")
    tab = []
    for d in ARMS:
        cells = []
        for ph in PHASES:
            k, n = agg[(ph, d)]
            cells.append(f"{pct(k, n)} ({k}/{n})")
            if ph == "partd_benign_corr":
                el, by, n2 = split[d]
                cells += [f"{pct(el, n2)} ({el})", f"{pct(by, n2)} ({by})"]
        tab.append(f"{NAME[d]} & " + " & ".join(cells) + " \\\\")
    tab.append("\\bottomrule")   # the body owns its closing rule (TL2025 file hooks break a rule after \\input)
    open(os.path.join(OUTD, "tabs", "tab_partd.tex"), "w").write("\n".join(tab) + "\n")
    print("partd valid rows:", len(rows), "models:", models)
    for ph in PHASES:
        print(ph, {d: f"{agg[(ph, d)][0]}/{agg[(ph, d)][1]}" for d in ARMS})
    print("corr split (elevation, bypass, n):", split)
    print("wrote numbers_partd.tex, tabs/tab_partd.tex")


if __name__ == "__main__":
    main()
