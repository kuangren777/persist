# Persist: code and data release

This release contains the test harness, the defenses, the run scripts, every frozen result row the paper's
analysis reads, and the scripts that turn those rows into each number, table and figure of the paper. The
harness gives a tool-using LLM agent a persistent memory store. In session 1 the agent reads a document and may
write to the store. In session 2 a benign user request is served from that store. An attack succeeds when an
attacker value from the untrusted document reaches a target argument of a session-2 side-effecting call. The
provenance gate tags each stored item with its source and refuses a target value backed only by untrusted
input. The pre-registration, amendments and analysis log were written before the corresponding data were
analysed and are in `docs/`.

## Reproduce the paper's numbers (offline)

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
./reproduce_all.sh                    # writes out/numbers*.tex, out/tabs/*.tex, out/figs/*.pdf
./reproduce_all.sh <paper folder>     # same, then compares with <paper folder>/numbers*.tex, tabs/, figs/
```

No network access and no key are needed, and the run takes about a minute. With a paper folder,
`reproduce_all.sh` first drops the macros listed in `macro_drops.tsv` that the paper's text does not print
(`prune_macros.py`, the same step the paper build runs; each line of `macro_drops.tsv` gives its reason). It then
compares byte for byte for the .tex files. For the PDF figures that `main.tex` includes it ignores only the
`/CreationDate` entry, which matplotlib stamps with the current time.

On the paper version at Overleaf commit c1f7725, all 31 .tex files are identical, 11 `numbers*.tex` and 20 `tabs/*.tex`. The 6 included figures are identical up to that date (Python 3.13, matplotlib 3.11.0). Other matplotlib versions can change figure bytes without changing the plotted values. `reproduce_all.sh` exits non-zero if a .tex file differs.

Every number is computed at full precision from integer counts and rounded once when it is written, with
ROUND_HALF_UP (`fmtnum.py`, used through `analyze.fx` and `analyze.fr`).

Every analyzer writes to `$PERSIST_OUT` (set by `reproduce_all.sh` to `out/`) and reads only the files named in
its explicit input list. `results/` holds exactly the files these lists name.

## Paper file, generator, input

| paper file | generator | input rows (under `results/`) |
|---|---|---|
| `numbers.tex`, `tabs/tab_rq1.tex`, `tab_rq2.tex`, `tab_rq3.tex`, `tab_contingency.tex`, `tab_scendef.tex`, `tab_rq5scen.tex` | `analyze.py` | `analyze.MAIN_GRID_FILES` (15 files: `grid_v6*.jsonl`, `grid_v8_ga*.jsonl`, `grid_v9_gaw.jsonl`, `grid_top_*.jsonl`) |
| `tabs/tab_rq3mech.tex`, the `Mech*` macros | `analyze.py` | `verify/rq3mech.json` (written by `verify_rq3mech.py`) |
| `tabs/tab_rq4.tex`, `tab_rq5.tex`, kept in the paper folder but not input by `main.tex` | `analyze.py` | `MAIN_GRID_FILES` |
| `numbers_esota.tex`, `tabs/tab_esota.tex`, `tab_esota_sig.tex` | `analyze_esota.py` | `_esota/grid_esota_{frontier,local,qwen8b,ropererun_frontier,ropererun_local}.jsonl` |
| `numbers_adaptive.tex`, `tabs/tab_rq4adapt.tex` | `analyze_adaptive.py` | `grid_adaptive_<model>.jsonl` for claude-sonnet-5, gemini-3.1-pro, gpt-5.6-sol, llama31-8b-local, qwen3-8b-yf |
| `numbers_adaptive_sens.tex`, `tabs/tab_rq4adapt_sens.tex` | `analyze_adaptive_sensitivity.py` | same five files |
| `numbers_delegated.tex`, `tabs/tab_delegated.tex` | `analyze_delegated.py` | `_a9/a9a_deleg_{frontier,llama31-8b-local,qwen3-32b-local,qwen3-8b-local}.jsonl`, `_esota/grid_delegated_frontier.jsonl` |
| `numbers_exp3.tex`, `tabs/tab_exp3.tex` | `analyze_exp3.py` | `_exp3/main/<model>_<condition>_<attack>_s<k>.jsonl` (64 shards, SleeperBench transfer) |
| `numbers_partc.tex`, `tabs/tab_partc.tex` | `analyze_partc.py` | `_a7/partc_clean.jsonl` |
| `numbers_partd.tex`, `tabs/tab_partd.tex`, `tab_partd_scen.tex` | `analyze_partd.py` | `grid_partd.jsonl` |
| `numbers_ablation.tex`, `tabs/tab_ablation.tex` | `analyze_ablation.py` | `_a7/a7c_ablation.jsonl`, `_a9/a9b_benign_abl.jsonl` |
| `numbers_exp0.tex`, `tabs/tab_exp0.tex` | `analyze_exp0.py` | `_a7/exp0_{deleg,relay}_{hidden,exposed}*.jsonl` (6 files); the post-hoc `DvP*` macros also read `_a7/a7d_p1clean.jsonl` and the archived tool-exposed batch `archive/tool_exposed_mixed_20261010/grid_adaptive_pc_frontier.jsonl` |
| `numbers_a10.tex` | `analyze_a10.py` | `_a10/a10_nonote.jsonl`, `grid_partd.jsonl`, `amlp_m3/online_*.jsonl` (AgentDojo rows: official CaMeL and the Persist taint approximation, 6 files) |
| `figs/fig_gap.pdf`, `fig_defense.pdf`, `fig_tradeoff.pdf`, `fig_heatmap.pdf`, `fig_scenario.pdf` | `make_figs.py` | `MAIN_GRID_FILES` |
| `figs/fig_method.pdf` | `fig_method_src.py` | none (diagram) |

`make_figs.py` also writes `fig_launder.pdf`, `fig_ablation.pdf` and `fig_wide.pdf`, which `main.tex` does not include.

## Layout

```
persistlab.py                 harness: scenarios, memory store, two-session chain, defenses, oracles
persistlab_adaptive.py        adaptive attacker (strategies A1 split, A2 encode, A3 cross-session relay)
rope_adapter.py               glue to the official ROPE code (arms rope and rope_raw), see below
run_grid.py                   main grid runner (phases attack, benign, launder, ablation, wide, wide_benign)
run_adaptive_grid.py          adaptive grid runner (Block A and the part c gate family)
run_esota.py                  head-to-head runner (arms none, prov_gate, prov_strict, ifc, louck, ppmf, rope)
run_delegated.py              delegated-benign runner
run_partd.py                  part d runner (two-principal corroboration, directory lookups)
verify_rq3mech.py             RQ3 mechanism batch (3 arms, 7 models, 20 seeds) -> results/verify/rq3mech.json
full_run.py, adaptive_run.py  early drivers of the first pilot; their outputs are not used by the paper
analyze*.py, make_figs.py     analysis, see the table above
fig_method_src.py             method diagram
compare_paper.py              comparison used by reproduce_all.sh
fmtnum.py                     shared renderer: full precision, one ROUND_HALF_UP
prune_macros.py, macro_drops.tsv   drop listed macros the paper does not print, each line with its reason
test_*.py                     unit and regression tests (pytest)
common_words_en.txt           word list used by the wide value recognizer in persistlab.py
results/                      frozen rows, one JSON object per trial (see below)
results/archive/              the archived tool-exposed batch, read only by the post-hoc DvP comparison
results/amlp_m3/              AgentDojo rows shared with the AMLP study, read only by analyze_a10.py
docs/                         pre-registration (EXPERIMENT_PLAN_*.md), adaptive templates and harm-oracle
                              amendment (ADAPTIVE_*.md), append-only analysis log (ANALYSIS_LOG.md)
```

Each row is one trial and carries `phase`, `model`, `scenario`, `defense`, `seed`, the outcome fields
(`persisted`, `activated`, `activated_variant`, `preserved`, `remembered`, `gate_blocked`, `write_blocks`),
the recorded session-2 tool calls `s2_calls`, and bookkeeping (`batch_id`, `served_root`, `backend`, `err`).
Adaptive rows add `strategy`, `template` and `held_out`. Rows with `err` or `error` set are failed trials and
are excluded from every denominator. When a cell occurs twice the analyzers keep the last row. The harm metric
recomputes activation from `s2_calls` (`analyze.harm_target`), so it does not depend on the stored
`activated` flag.

Rows that a documented erratum replaced are not part of this release. `docs/ANALYSIS_LOG.md` records each
replacement and its reason.

## Tests

```
pytest -q test_analyzer_inputs.py test_analyze_partc.py test_analyze_partd.py test_adaptive.py test_ifc.py test_top_patch.py
ROPE_SRC=<ROPE checkout>/src pytest -q test_*.py      # all 26 tests, including test_rope.py and test_partd.py
```

All tests are offline. `test_analyzer_inputs.py` checks that the analyzers read their explicit input lists and
reproduce `NumTrials` = 18683 and the adaptive worst-case cells.

## Running new trials

Agent runs call models and need these environment variables:

| variable | meaning |
|---|---|
| `LLM_API_BASE` | OpenAI-compatible base URL (with `/v1`) of the gateway that serves the six hosted models |
| `LLM_API_KEY` | key for that gateway |
| `PORT_<model>` | local vLLM port of an open model, `<model>` with `-` replaced by `_`, e.g. `PORT_qwen3_8b_local` (defaults 8021, 8023, 8031, 8034 for qwen3-8b-local, llama31-8b-local, qwen3-32b-local, qwen3-8b-yf on 127.0.0.1) |
| `PERSIST_RUNS` | directory for the per-trial memory stores (default `runs/`) |
| `ROPE_SRC` | `src/` directory of the official ROPE code (default `third_party/ROPE/src`) |
| `ROPE_ROUTER_MODEL` | router model for the ROPE arms (default `claude-opus-4-8`) |
| `MODELS`, `ARMS`, `PHASES`, `SCEN`, `NA`, `NB`, `NS`, `OUT`, `BATCH_ID`, `WORKERS` | runner grid and output, see each runner's docstring |

The hosted models are claude-sonnet-5, gpt-5.6-sol, gemini-3.1-pro, deepseek-v4.1-flash, glm-5.3 and kimi-k3.
The open models were served with vLLM: Qwen/Qwen3-8B (qwen3-8b-local and, on a second server, qwen3-8b-yf),
meta-llama/Llama-3.1-8B-Instruct and Qwen/Qwen3-32B. Before each local run the runners check that the port
serves the expected model (`persistlab.assert_served_root`) and record the served model in `served_root`.

The ROPE arms use the official code, github.com/xhOwenMa/ROPE at commit
`64495e16e640d687e06e6b1b6cee6dccc5b9b7cb` (MIT license), unchanged:

```
git clone https://github.com/xhOwenMa/ROPE third_party/ROPE && git -C third_party/ROPE checkout 64495e16
```

Model outputs vary between calls, so re-running trials gives new rows. The paper's numbers come from the rows
in `results/`.

## License

MIT, see `LICENSE`. See `PRIVACY.md` for what was removed before release.
