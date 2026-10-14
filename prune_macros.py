"""Remove macros listed in review/macro_drops.tsv from the generated numbers*.tex of a paper dir, but only when the
macro is not referenced; a listed macro that the text uses is kept and reported, so a printed number is never hidden.
Usage: python3 review/prune_macros.py paper-overleaf-top [text_dir]
(text_dir: where the referencing .tex lives when the numbers*.tex were generated elsewhere, as in the release)"""
import glob, os, re, sys
root = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
pats = [(re.compile(l.split("\t")[0]), l.split("\t")[1].strip()) for l in open(os.path.join(here, "macro_drops.tsv"))
        if l.strip() and not l.startswith("#")]
texs = glob.glob(os.path.join(sys.argv[2] if len(sys.argv) > 2 else root, "**", "*.tex"), recursive=True)
nums = [f for f in glob.glob(os.path.join(root, "**", "*.tex"), recursive=True) if os.path.basename(f).startswith("numbers")]
body = ""
for f in texs:
    if os.path.basename(f).startswith("numbers"):
        continue
    body += re.sub(r"(?m)^\s*%.*$", "", open(f, errors="ignore").read())
used = set(re.findall(r"\\([A-Za-z]+)", body))
dropped, bad = 0, []
for f in nums:
    keep = []
    for l in open(f):
        m = re.match(r"\\newcommand\{\\([A-Za-z]+)\}", l)
        if m and any(p.fullmatch(m.group(1)) for p, _ in pats):
            if m.group(1) in used:
                bad.append(m.group(1)); keep.append(l)
            else:
                dropped += 1
            continue
        keep.append(l)
    open(f, "w").write("".join(keep))
print(f"dropped {dropped}")
if bad:   # a pattern also covers a printed macro; it is kept, never hidden
    print(f"kept {len(bad)} listed-but-referenced macros (printed in the text)")
