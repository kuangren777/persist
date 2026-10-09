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
NAME = {"none": "no defense", "prov_gate": "reference gate", "louck": "Louck", "ppmf": "PPMF", "rope": "ROPE"}
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
    return f"{100.0 * k / n:.1f}" if n else "0.0"


def main():
    rows = load()
    agg = aggregate(rows)
    out = []
    for ph, pt in PHASES.items():
        for d in ARMS:
            k, n = agg[(ph, d)]
            out.append(f"\\newcommand{{\\Partd{pt}{TAG[d]}N}}{{{k}/{n}}}")
            out.append(f"\\newcommand{{\\Partd{pt}{TAG[d]}Pct}}{{{pct(k, n)}}}")
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
        tab.append(f"{NAME[d]} & " + " & ".join(cells) + " \\\\")
    tab.append("\\bottomrule")   # the body owns its closing rule (TL2025 file hooks break a rule after \\input)
    open(os.path.join(OUTD, "tabs", "tab_partd.tex"), "w").write("\n".join(tab) + "\n")
    print("partd valid rows:", len(rows), "models:", models)
    for ph in PHASES:
        print(ph, {d: f"{agg[(ph, d)][0]}/{agg[(ph, d)][1]}" for d in ARMS})
    print("wrote numbers_partd.tex, tabs/tab_partd.tex")


if __name__ == "__main__":
    main()
