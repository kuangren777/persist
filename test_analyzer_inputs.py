"""Regression tests for the analyzers' explicit input lists. Each analyzer reads a fixed list of result files,
so files added to results/ later (grid_partd.jsonl, grid_adaptive_pc_*) no longer leak into earlier analyses,
and a rerun reproduces the frozen macros. All output goes to $PERSIST_OUT (a tmp dir), never the paper folder."""
import os, re, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
import analyze_adaptive as AD
import analyze_esota as E
import analyze_delegated as D


def _macros(path):
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", open(path).read()))


def test_input_lists_exist_and_exclude_later_families():
    for f in A.MAIN_GRID_FILES + AD.ADAPTIVE_FILES:
        assert os.path.exists(os.path.join(A.RES, f)), f
    for f in E.ESOTA_FILES + D.DELEG_FILES:
        assert os.path.exists(os.path.join(E.RES, f)), f
    assert not any("partd" in f or "adaptive" in f for f in A.MAIN_GRID_FILES)
    assert not any("_pc_" in f or "pilot" in f for f in AD.ADAPTIVE_FILES)
    assert A.MAIN_GRID_FILES == sorted(A.MAIN_GRID_FILES)   # keep-last dedup reads them in sorted order


def test_glob_would_have_leaked():
    # documents the defect the explicit list fixes: the old glob also matched the part d grid
    g = {os.path.basename(p) for p in glob.glob(os.path.join(A.RES, "grid*.jsonl")) if "grid_adaptive" not in p}
    assert "grid_partd.jsonl" in g and "grid_partd.jsonl" not in A.MAIN_GRID_FILES


def test_main_and_adaptive_reproduce_frozen_macros(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PERSIST_OUT", str(tmp_path))
    assert A.out_dir() == str(tmp_path)
    A.main(); AD.main()
    m = _macros(tmp_path / "numbers.tex")
    assert m["NumTrials"] == "18683"            # 23002 with the old glob (4319 part d rows leaked in)
    a = _macros(tmp_path / "numbers_adaptive.tex")
    assert a["AdaptAOneNoneWorstN"] == "138/240"   # 195/480 with the old glob (part c rows leaked in)
    assert a["AdaptAOneProvGateHeldN"] == "24/480"
    assert (tmp_path / "TABLES.md").exists()
