#!/usr/bin/env bash
# Regenerate every numbers*.tex, tabs/*.tex and figure of the paper into out/ from the frozen rows in results/,
# offline (no model call, no key). With a paper folder argument, compare the outputs against it:
#   ./reproduce_all.sh                  # generate into out/
#   ./reproduce_all.sh path/to/paper    # generate, then compare with path/to/paper/{numbers*.tex,tabs/,figs/}
# Exit status is non-zero if any .tex file differs from the paper folder.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out
mkdir -p out/tabs out/figs out/logs
export PERSIST_OUT="$PWD/out"
export MPLBACKEND=Agg

for a in analyze analyze_adaptive analyze_adaptive_sensitivity analyze_esota analyze_delegated \
         analyze_partc analyze_partd make_figs; do
  echo "[reproduce] $a.py"
  python3 "$a.py" > "out/logs/$a.log"
done
echo "[reproduce] fig_method_src.py"
python3 fig_method_src.py out/figs/fig_method > out/logs/fig_method_src.log

if [ $# -ge 1 ]; then
  python3 compare_paper.py out "$1"
fi
