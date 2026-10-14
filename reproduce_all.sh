#!/usr/bin/env bash
# Regenerate every numbers*.tex, tabs/*.tex and figure of the paper into out/ from the frozen rows in results/,
# offline (no model call, no key). With a paper folder argument, compare the outputs against it:
#   ./reproduce_all.sh                  # generate into out/
#   ./reproduce_all.sh path/to/paper    # generate, prune unprinted listed macros, then compare with
#                                       # path/to/paper/{numbers*.tex,tabs/,figs/}
# Exit status is non-zero if any .tex file differs from the paper folder.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out
mkdir -p out/tabs out/figs out/logs
export PERSIST_OUT="$PWD/out"
export MPLBACKEND=Agg

# same order as the project's regen_numbers.sh
for a in analyze analyze_esota analyze_adaptive analyze_adaptive_sensitivity analyze_delegated analyze_exp3 \
         analyze_partc analyze_partd analyze_ablation analyze_exp0 analyze_a10 make_figs; do
  echo "[reproduce] $a.py"
  python3 "$a.py" > "out/logs/$a.log"
done
echo "[reproduce] fig_method_src.py"
python3 fig_method_src.py out/figs/fig_method > out/logs/fig_method_src.log

if [ $# -ge 1 ]; then
  # drop the macros listed in macro_drops.tsv that the paper's text does not print, as the paper build does
  python3 prune_macros.py out "$1"
  python3 compare_paper.py out "$1"
fi
