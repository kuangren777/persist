"""Amendment 10 analyses. P1: note-removed counterfactual, paired with the existing corroboration rows on the same five
frontier models (kimi-k3 excluded) by (model, scenario, seed); preserved oracle unchanged; McNemar. P2: the Persist
taint-matching approximation (persist_taint arm, AMLP AgentDojo harness) against official CaMeL with its policies on the
same jobs; benign utility and AgentDojo attack success per model, temperature 0 (decision run) and 1.0 (the Persist
configuration); task-level cell counts. Emits numbers_a10.tex into analyze.out_dir()."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
AMLP = os.path.join(RES, "amlp_m3")
M5 = {"claude-sonnet-5", "gpt-5.6-sol", "gemini-3.1-pro", "deepseek-v4.1-flash", "glm-5.3"}
TAG = {"none": "None", "louck": "Louck", "ppmf": "Ppmf"}
MODELS = {"gpt-4o-mini-2024-07-18": "FourOMini", "gpt-4.1-mini-2025-04-14": "FourOneMini"}


def _rows(path, phase):
    d = {}
    for l in open(path):
        r = json.loads(l)
        if r.get("err") or r.get("error") or r.get("phase") != phase or r["model"] not in M5:
            continue
        d[(r["model"], r["scenario"], r["defense"], r["seed"])] = r
    return d


def p1(out):
    kept = _rows(os.path.join(RES, "grid_partd.jsonl"), "partd_benign_corr")
    rem = _rows(os.path.join(RES, "_a10", "a10_nonote.jsonl"), "partd_benign_corrnonote")
    for d, t in TAG.items():
        ks = [k for k in rem if k[2] == d and k in kept]
        a = [bool(kept[k]["preserved"]) for k in ks]; b = [bool(rem[k]["preserved"]) for k in ks]
        p = A.scen_test([(k[1], x, y) for k, x, y in zip(ks, a, b)])[1]
        out += [f"\\newcommand{{\\NoNoteKept{t}N}}{{{sum(a)}/{len(ks)}}}",
                f"\\newcommand{{\\NoNoteRemoved{t}N}}{{{sum(b)}/{len(ks)}}}",
                f"\\newcommand{{\\NoNoteRemoved{t}Pct}}{{{A.fx(A.fr(sum(b), len(ks), True), '.1f')}}}",
                f"\\newcommand{{\\NoNoteKept{t}Pct}}{{{A.fx(A.fr(sum(a), len(ks), True), '.1f')}}}",
                f"\\newcommand{{\\NoNoteP{t}}}{{{'below 0.001' if p < 0.001 else A.fx(p, '.3f')}}}"]
        print(f"P1 {d}: kept {sum(a)}/{len(ks)} removed {sum(b)}/{len(ks)} p={p:.3g}")


def _load(path):
    return [r for r in map(json.loads, open(path)) if not r.get("err")]


def p2(out):
    for m, t in MODELS.items():
        cam = _load(os.path.join(AMLP, f"online_{m}__camel.jsonl"))
        cells = {(r["suite"], r["ut"], r["it"] or "", r["rep"]) for r in cam}
        for arm, f in (("Camel", f"online_{m}__camel.jsonl"), ("TaintZero", f"online_{m}__persist_taint_t0.jsonl"),
                       ("TaintOne", f"online_{m}__persist_taint.jsonl")):
            rs = [r for r in _load(os.path.join(AMLP, f)) if (r["suite"], r["ut"], r["it"] or "", r["rep"]) in cells]
            ben = [r for r in rs if not r["it"]]; atk = [r for r in rs if r["it"]]
            u = sum(bool(r["utility"]) for r in ben); s = sum(bool(r["security"]) for r in atk)
            out += [f"\\newcommand{{\\PTwo{arm}Util{t}}}{{{A.fx(A.fr(u, len(ben), True), '.1f')}}}",
                    f"\\newcommand{{\\PTwo{arm}Atk{t}}}{{{A.fx(A.fr(s, len(atk), True), '.1f')}}}"]
            print(f"P2 {m} {arm}: benign {u}/{len(ben)} attack {s}/{len(atk)}")
        # task-level cells where the temperature-0 approximation lets more attacks through than CaMeL
        cc = defaultdict(list); pc = defaultdict(list)
        for r in cam:
            if r["it"]:
                cc[(r["suite"], r["ut"], r["it"])].append(bool(r["security"]))
        for r in _load(os.path.join(AMLP, f"online_{m}__persist_taint_t0.jsonl")):
            if r["it"]:
                pc[(r["suite"], r["ut"], r["it"])].append(bool(r["security"]))
        worse = sum(1 for k in cc if k in pc and sum(pc[k]) / len(pc[k]) > sum(cc[k]) / len(cc[k]))
        better = sum(1 for k in cc if k in pc and sum(pc[k]) / len(pc[k]) < sum(cc[k]) / len(cc[k]))
        out += [f"\\newcommand{{\\PTwoWorseCells{t}}}{{{worse}}}", f"\\newcommand{{\\PTwoAtkCells{t}}}{{{len(cc)}}}",
                f"\\newcommand{{\\PTwoBetterCells{t}}}{{{better}}}"]


def main():
    out = ["% auto: analyze_a10.py"]
    p1(out); p2(out)
    open(os.path.join(A.out_dir(), "numbers_a10.tex"), "w").write("\n".join(out) + "\n")
    print("wrote numbers_a10.tex")


if __name__ == "__main__":
    main()
