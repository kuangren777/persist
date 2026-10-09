"""Compare regenerated outputs with a paper folder. Usage: python3 compare_paper.py <out_dir> <paper_dir>.

.tex files (numbers*.tex, tabs/*.tex): byte comparison. Figures: the PDFs the paper's main.tex includes are
compared byte for byte after removing the /CreationDate and /ModDate entries, which matplotlib stamps with the
current time. A figure that differs beyond those dates is reported but does not fail the run (font and
matplotlib versions change PDF bytes). Exits 1 if any .tex file differs or is missing."""
import os, re, sys

out, paper = sys.argv[1], sys.argv[2]


def strip_dates(b):
    return re.sub(rb"/(CreationDate|ModDate) \(D:[^)]*\)", b"", b)


tex = sorted([f for f in os.listdir(paper) if re.fullmatch(r"numbers.*\.tex", f)] +
             ["tabs/" + f for f in os.listdir(os.path.join(paper, "tabs")) if f.endswith(".tex")])
bad = 0
print(f"{'file':34} result")
for f in tex:
    a, b = os.path.join(out, f), os.path.join(paper, f)
    if not os.path.exists(a):
        print(f"{f:34} MISSING in {out}"); bad += 1; continue
    same = open(a, "rb").read() == open(b, "rb").read()
    print(f"{f:34} {'identical' if same else 'DIFFERS'}")
    bad += not same

main = os.path.join(paper, "main.tex")
figs = sorted(set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", open(main).read()))) \
    if os.path.exists(main) else []
for g in figs:
    name = os.path.basename(g)
    if not name.endswith(".pdf"):
        name += ".pdf"
    a, b = os.path.join(out, "figs", name), os.path.join(paper, "figs", name)
    if not os.path.exists(b):
        b = os.path.join(paper, name)
    if not os.path.exists(a) or not os.path.exists(b):
        print(f"figs/{name:29} MISSING"); continue
    A, B = open(a, "rb").read(), open(b, "rb").read()
    res = "identical" if A == B else ("identical except PDF dates" if strip_dates(A) == strip_dates(B)
                                      else "differs (check versions)")
    print(f"figs/{name:29} {res}")

print(f"{len(tex) - bad} of {len(tex)} .tex files identical")
sys.exit(1 if bad else 0)
