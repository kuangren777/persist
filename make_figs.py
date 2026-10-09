"""Generate the data figures from the main-grid files (analyze.MAIN_GRID_FILES) into <out>/figs/*.pdf,
<out> = analyze.out_dir() ($PERSIST_OUT, else paper-overleaf-top/, else out/).
Script-generated, reproducible. No hand-placed numbers."""
import json, glob, os, sys, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as _A
FIG = os.path.join(_A.out_dir(), "figs")
os.makedirs(FIG, exist_ok=True)
MODELS = ["claude-sonnet-5", "gpt-5.6-sol", "gemini-3.1-pro", "deepseek-v4.1-flash",
          "glm-5.3", "kimi-k3", "qwen3-8b-local", "llama31-8b-local", "qwen3-32b-local"]
SHORT = {"claude-sonnet-5": "claude", "gpt-5.6-sol": "gpt-5.6", "gemini-3.1-pro": "gemini-3.1",
         "deepseek-v4.1-flash": "deepseek", "glm-5.3": "glm-5.3", "kimi-k3": "kimi",
         "qwen3-8b-local": "qwen3-8b", "llama31-8b-local": "llama-3.1-8b", "qwen3-32b-local": "qwen3-32b"}
DEF = ["none", "write_filter", "spotlight", "whitelist", "provenance"]
DEFLAB = {"none": "No defense", "write_filter": "Write filter", "spotlight": "Spotlight",
          "whitelist": "Domain allow-list", "provenance": "Annotated gate"}
SCEN = ["recipient_replace", "cc_exfil", "webhook_exfil", "payment_account", "add_admin",
        "forwarding_rule", "dependency_url", "scheduled_task"]
plt.rcParams.update({"font.size": 11, "axes.spexpansion" if False else "axes.grid": True,
                     "grid.alpha": 0.3, "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"none": "#B0B0B0", "write_filter": "#6BAED6", "spotlight": "#9E9AC8",
     "whitelist": "#FDAE6B", "provenance": "#31A354"}


def load():
    from analyze import harm_target, MAIN_GRID_FILES   # same metric and same input files as the tables
    seen = {}
    for f in [os.path.join(_A.RES, x) for x in MAIN_GRID_FILES]:
        v8 = "grid_v8_ga" in os.path.basename(f)   # v8 batch contributes only prov_gate
        for l in open(f):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("err") or r.get("error"):   # failed trial ("err") or wrapped exception ("error")
                continue
            if v8 and r.get("defense") != "prov_gate":
                continue
            if r.get("phase") in ("attack", "launder", "wide", "ablation"):
                r["activated_exact"] = r.get("activated", False)
                r["activated"] = harm_target(r)   # unify every figure on the harm metric
                r["persisted"] = bool(r.get("persisted", False)) or r["activated"]  # activation implies persistence
            if not (r.get("phase") and r.get("model") and r.get("scenario") and r.get("defense") is not None and r.get("seed") is not None):
                continue
            if r["model"] not in MODELS:
                continue
            k = (r["phase"], r["model"], r["scenario"], r["defense"], r["seed"])
            seen[k] = r   # keep-last: a later rerun of the same cell overrides, matching the on-disk store
    return list(seen.values())


def rate(rows, field="activated"):
    rows = list(rows)
    return (sum(r.get(field, False) for r in rows) / len(rows)) if rows else 0.0


def wil(rows, field="activated", z=1.96):
    n = len(rows)
    if not n:
        return 0, 0, 0
    p = sum(r.get(field, False) for r in rows) / n
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    return p, max(0, c - h), min(1, c + h)


def method_fig():
    """Clean two-session data-flow diagram, boxes with labels inside, arrows annotated clear of nodes."""
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig, ax = plt.subplots(figsize=(7.2, 3.6)); ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.grid(False)

    def box(x, y, w, h, title, sub, fc):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=fc, ec="#333333", lw=1.2))
        ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=9.5, weight="bold")
        if sub:
            ax.text(x + w / 2, y + h - 0.72, sub, ha="center", va="top", fontsize=8)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                                     lw=1.3, color="#333333", shrinkA=2, shrinkB=2))

    def glabel(xc, y, s):   # label centered in a gap, clear of the boxes
        ax.text(xc, y, s, ha="center", va="center", fontsize=7.5, color="#555555")

    # Session one (write), top row. Boxes: doc 0.2-2.4, agent 3.0-5.2, store 5.8-9.6; gaps hold labels.
    ax.text(0.1, 6.7, "Session 1: benign task, reads an untrusted document", fontsize=8.5,
            style="italic", color="#555555")
    box(0.2, 4.6, 2.2, 1.6, "Untrusted", "document", "#F2E6E6")
    box(3.0, 4.6, 2.2, 1.6, "Session-1", "agent", "#E8EEF6")
    box(5.8, 4.6, 3.8, 1.6, "Project store", "value = user if in a user\nmessage, else agent_tool", "#EDEDED")
    arrow(2.4, 5.4, 3.0, 5.4); glabel(2.7, 5.65, "reads")
    arrow(5.2, 5.4, 5.8, 5.4); glabel(5.5, 5.65, "writes")

    # cross-session link (down the right side)
    arrow(7.7, 4.6, 7.7, 3.0); glabel(8.5, 3.8, "store persists")

    # Session two (activate), bottom row. Boxes mirror the top row.
    ax.text(0.1, 2.7, "Session 2: fresh agent, a different benign task", fontsize=8.5,
            style="italic", color="#555555")
    box(5.8, 1.0, 3.8, 1.6, "Session-2 agent", "loads the store", "#E8EEF6")
    box(3.0, 1.0, 2.2, 1.6, "Read-time gate", "refuse an\nagent_tool target", "#E6F0E6")
    box(0.2, 1.0, 2.2, 1.6, "Tool call", "allow or block", "#EDEDED")
    arrow(5.8, 1.8, 5.2, 1.8); glabel(5.5, 2.05, "call")
    arrow(3.0, 1.8, 2.4, 1.8); glabel(2.7, 2.05, "gate")
    fig.savefig(os.path.join(FIG, "fig_method.pdf")); plt.close(fig)


def main():
    # fig_method.pdf in the paper is the later hand-laid version drawn by paper-overleaf-top/figs/fig_method_src.py
    # (release: fig_method_src.py); method_fig() above is the earlier draft and would overwrite it, so it is not called.
    rows = load()
    atk = [r for r in rows if r["phase"] == "attack"]
    ben = [r for r in rows if r["phase"] == "benign"]
    lau = [r for r in rows if r["phase"] == "launder"]
    abl = [r for r in rows if r["phase"] == "ablation"]
    xs = range(len(MODELS))

    # Fig 1 — RQ1 activation gap: persistence vs end-to-end per model
    fig, ax = plt.subplots(figsize=(7, 3.2))
    none = [r for r in atk if r["defense"] == "none"]
    per = [rate([r for r in none if r["model"] == m], "persisted") for m in MODELS]
    e2e = [rate([r for r in none if r["model"] == m], "activated") for m in MODELS]
    w = 0.38
    ax.bar([x - w/2 for x in xs], per, w, label="Persistence", color="#9ECAE1")
    ax.bar([x + w/2 for x in xs], e2e, w, label="End-to-end (activation)", color="#DE2D26")
    ax.set_xticks(list(xs)); ax.set_xticklabels([SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_ylabel("rate"); ax.set_ylim(0, 1.05); ax.legend()
    ax.set_title("Persistence and end-to-end harm, by model")
    fig.savefig(os.path.join(FIG, "fig_gap.pdf")); plt.close(fig)

    # Fig 2 — RQ2 end-to-end per defense, grouped by model
    fig, ax = plt.subplots(figsize=(8, 3.4))
    w = 0.16
    for i, d in enumerate(DEF):
        vals = [rate([r for r in atk if r["model"] == m and r["defense"] == d]) for m in MODELS]
        ax.bar([x + (i - 2) * w for x in xs], vals, w, label=DEFLAB[d], color=C[d])
    ax.set_xticks(list(xs)); ax.set_xticklabels([SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_ylabel("end-to-end success ↓"); ax.set_ylim(0, 1.0); ax.legend(ncol=3, fontsize=8)
    ax.set_title("Harmful end-to-end per defense, by model")
    fig.savefig(os.path.join(FIG, "fig_defense.pdf")); plt.close(fig)

    # Fig 3 — tradeoff scatter: interception vs benign preservation, per defense (pooled)
    fig, ax = plt.subplots(figsize=(5.2, 4))
    base = rate([r for r in atk if r["defense"] == "none"])
    for d in DEF:
        if d == "none":
            continue
        inter = 1 - rate([r for r in atk if r["defense"] == d]) / base if base else 0
        pres = rate([r for r in ben if r["defense"] == d], "preserved")
        ax.scatter(pres, inter, s=120, color=C[d], edgecolor="k", zorder=3)
        ax.annotate(DEFLAB[d], (pres, inter), fontsize=9, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("benign preservation →"); ax.set_ylabel("attack interception →")
    ax.set_xlim(0, 1.05); ax.set_ylim(0, 1.05)
    ax.set_title("Interception vs benign preservation")
    fig.savefig(os.path.join(FIG, "fig_tradeoff.pdf")); plt.close(fig)

    # Fig 4 — heatmap scenario x model, end-to-end none
    fig, ax = plt.subplots(figsize=(7.5, 4))
    M = [[rate([r for r in atk if r["defense"] == "none" and r["model"] == m and r["scenario"] == sc])
          for m in MODELS] for sc in SCEN]
    im = ax.imshow(M, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(MODELS))); ax.set_xticklabels([SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_yticks(range(len(SCEN))); ax.set_yticklabels(SCEN)
    for i in range(len(SCEN)):
        for j in range(len(MODELS)):
            ax.text(j, i, f"{M[i][j]:.1f}", ha="center", va="center", fontsize=7,
                    color="white" if M[i][j] > 0.5 else "black")
    fig.colorbar(im, ax=ax, label="end-to-end (no defense)")
    ax.set_title("Harmful end-to-end by scenario and model")
    fig.savefig(os.path.join(FIG, "fig_heatmap.pdf")); plt.close(fig)

    # Fig 5 — RQ4 laundering harm per model: no defense, recommended gate alone, annotated gate
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    w = 0.26
    lau_none = [rate([r for r in lau if r["model"] == m and r["defense"] == "none"]) for m in MODELS]
    lau_gate = [rate([r for r in lau if r["model"] == m and r["defense"] == "prov_gate"]) for m in MODELS]
    lau_prov = [rate([r for r in lau if r["model"] == m and r["defense"] == "provenance"]) for m in MODELS]
    for i, (vals, lab, col) in enumerate([(lau_none, "no defense", "#B0B0B0"),
                                           (lau_gate, "gate alone (ours)", "#31A354"),
                                           (lau_prov, "annotated gate", "#DE2D26")]):
        ax.bar([x + (i - 1) * w for x in xs], vals, w, label=lab, color=col)
    ax.set_xticks(list(xs)); ax.set_xticklabels([SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_ylabel("harmful end-to-end ↓"); ax.set_ylim(0, 1.0); ax.legend(fontsize=8)
    ax.set_title("Harmful end-to-end under laundering, by model")
    fig.savefig(os.path.join(FIG, "fig_launder.pdf")); plt.close(fig)

    # Fig 6 — ablation: annotate-only / gate-only / both, interception pooled per model
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    w = 0.26
    for i, (d, src, lab, col) in enumerate([("prov_annotate", abl, "annotate only", "#C6DBEF"),
                                             ("prov_gate", abl, "gate only", "#6BAED6"),
                                             ("provenance", atk, "annotated gate", "#31A354")]):
        vals = []
        for m in MODELS:
            b = rate([r for r in atk if r["model"] == m and r["defense"] == "none"])
            v = rate([r for r in src if r["model"] == m and r["defense"] == d])
            vals.append(1 - v / b if b else 0)
        ax.bar([x + (i - 1) * w for x in xs], vals, w, label=lab, color=col)
    ax.set_xticks(list(xs)); ax.set_xticklabels([SHORT[m] for m in MODELS], rotation=30, ha="right")
    ax.set_ylabel("interception ↑"); ax.set_ylim(0, 1.05); ax.legend(fontsize=9)
    ax.set_title("Component ablation, interception by model")
    fig.savefig(os.path.join(FIG, "fig_ablation.pdf")); plt.close(fig)

    # Fig 7 — per-scenario breakdown: none vs provenance end-to-end, pooled over models
    fig, ax = plt.subplots(figsize=(8, 3.2))
    w = 0.38
    n_v = [rate([r for r in atk if r["defense"] == "none" and r["scenario"] == sc]) for sc in SCEN]
    p_v = [rate([r for r in atk if r["defense"] == "provenance" and r["scenario"] == sc]) for sc in SCEN]
    xs2 = range(len(SCEN))
    ax.bar([x - w/2 for x in xs2], n_v, w, label="No defense", color="#B0B0B0")
    ax.bar([x + w/2 for x in xs2], p_v, w, label=DEFLAB["provenance"], color="#31A354")
    ax.set_xticks(list(xs2)); ax.set_xticklabels(SCEN, rotation=30, ha="right")
    ax.set_ylabel("end-to-end ↓"); ax.set_ylim(0, 1.0); ax.legend()
    ax.set_title("Harmful end-to-end by scenario, pooled over models")
    fig.savefig(os.path.join(FIG, "fig_scenario.pdf")); plt.close(fig)

    # Fig 8 — RQ5 surface-form harm (normalized target-arg) under no defense / annotated gate / gate-alone / prov_wide
    from analyze import harm_target as _ht
    wide = [r for r in rows if r["phase"] == "wide"]
    if wide:
        def hrate(rs):
            rs = list(rs)
            return (sum(_ht(r) for r in rs) / len(rs)) if rs else 0.0
        fig, ax = plt.subplots(figsize=(8, 3.2))
        w = 0.2
        for i, (d, lab, col) in enumerate([("none", "no defense", "#B0B0B0"),
                                           ("provenance", "annotated gate", "#DE2D26"),
                                           ("prov_gate", "gate alone", "#FD8D3C"),
                                           ("prov_wide", "prov_wide", "#31A354")]):
            vals = [hrate([r for r in wide if r["model"] == m and r["defense"] == d]) for m in MODELS]
            ax.bar([x + (i - 1.5) * w for x in xs], vals, w, label=lab, color=col)
        ax.set_xticks(list(xs)); ax.set_xticklabels([SHORT[m] for m in MODELS], rotation=30, ha="right")
        ax.set_ylabel("harmful end-to-end ↓"); ax.set_ylim(0, 1.0); ax.legend(fontsize=8)
        ax.set_title("Surface-form harm, by model")
        fig.savefig(os.path.join(FIG, "fig_wide.pdf")); plt.close(fig)

    print("wrote figures:", sorted(os.listdir(FIG)))


if __name__ == "__main__":
    main()
