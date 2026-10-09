import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch

out = sys.argv[1] if len(sys.argv) > 1 else "persist_fig_pm"
fig, ax = plt.subplots(figsize=(7.0, 3.3))
ax.set_xlim(-1, 166); ax.set_ylim(6, 68); ax.axis("off")
GRAY, BLUE, ORANGE, EDGE = "#f2f2f2", "#e8eef7", "#fdf0e3", "#444444"
FS, FSS = 8, 6.8


def box(x, y, w, h, text, fc=GRAY, fs=FS, align="center"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.5",
                                fc=fc, ec=EDGE, lw=1.0))
    tx = x if align == "center" else x - w / 2 + 1.5
    ax.text(tx, y, text, ha=align, va="center", fontsize=fs, linespacing=1.4)


def arrow(p, q, label=None, at=None, ha="center", style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=10, lw=1.0,
                                 color=EDGE, linestyle=ls, shrinkA=0, shrinkB=0))
    if label:
        ax.text(*at, label, ha=ha, va="center", fontsize=FSS)


# column headers
for x, t in [(24, "session 1 · write"), (76, "store"), (132, "session 2 · activate")]:
    ax.text(x, 66, t, ha="center", fontsize=FS, fontweight="bold")

# session 1
box(12, 58, 21, 6, r"$u$: user msg")
box(43, 58, 29, 6, r"$d$: untrusted doc", fc="#f7e6e6")
box(24, 46, 38, 6, r"agent writes note $n$")
box(24, 34, 38, 6, r"tag$(v)$ for each $v\in n$", fc=BLUE)
box(24, 20, 44, 6, r"$v \in u \Rightarrow$ user, else agent_tool", fs=FSS, fc="white")
arrow((12, 54.5), (18, 49.5)); arrow((43, 54.5), (33, 49.5))
arrow((24, 42.5), (24, 37.5))
arrow((24, 30.5), (24, 23.5), style="-", ls=":")

# store
box(76, 38, 40, 14, "$M$:\n" r"mgr@int $\mapsto$ user" "\n" r"arch@ext $\mapsto$ agent_tool",
    fc="#ececec", fs=FSS, align="left")
arrow((43.5, 34), (55.5, 36), "save", at=(49.5, 38))
ax.text(76, 25.5, r"$U_M=\{v : \mathrm{tag}(v)=\mathrm{user}\}$", ha="center", fontsize=FSS)

# session 2
box(117, 58, 22, 6, r"$u'$: user msg")
box(146, 58, 28, 6, r"call $c$ (targets)")
dx, dy, dw, dh = 131, 38, 34, 17
ax.add_patch(Polygon([(dx - dw / 2, dy), (dx, dy + dh / 2), (dx + dw / 2, dy), (dx, dy - dh / 2)],
                     closed=True, fc=ORANGE, ec=EDGE, lw=1.0))
ax.text(dx, dy, "target$(c)\\subseteq$\n$U_M\\cup u'$ ?", ha="center", va="center", fontsize=FS,
        linespacing=1.3)
arrow((117, 54.5), (124, 44.5)); arrow((146, 54.5), (138, 44.5))
arrow((96.5, 38), (113.5, 38), "load", at=(105, 40.2))
box(155, 22, 19, 6, r"execute $c$", fc="#e6f4e6")
box(125, 18, 24, 6, "refuse + log", fc="#f7e6e6")
arrow((143, 33.5), (152, 25.5), "yes", at=(151, 31))
arrow((127, 31), (125.5, 21.5), "no", at=(129.5, 26))
ax.text(125, 10.5, r"match: exact $\parallel$ normalized", ha="center", fontsize=FSS)

fig.savefig(out + ".pdf", bbox_inches="tight", pad_inches=0.03)
fig.savefig(out + ".png", dpi=300, bbox_inches="tight", pad_inches=0.03)
