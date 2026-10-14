"""Tests for analyze_partc.py: the family-grid table body (tabs/tab_partc.tex) agrees with the macros and
carries the valid denominators (one PPMF relay cell missing, ANALYSIS_LOG)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_partc as C


def test_table_matches_macros(tmp_path, monkeypatch):
    monkeypatch.setenv("PERSIST_OUT", str(tmp_path))   # never write into the paper folder from a test
    C.main()
    tab = open(tmp_path / "tabs" / "tab_partc.tex").read().strip().splitlines()
    mac = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", open(tmp_path / "numbers_partc.tex").read()))
    assert tab[-1] == "\\bottomrule"
    tab = [l for l in tab[:-1] if not l.startswith("\\quad")]   # p rows under each gate
    assert [l.split(" & ")[0] for l in tab] == ["reference gate", "loose taint matching", "corroboration gate", "authority gate", "ROPE (record)"]
    tags = ["ProvGate", "Ifc", "Louck", "Ppmf", "Rope"]
    for line, tag in zip(tab, tags):
        cells = line.rstrip(" \\").split(" & ")[1:]
        for cell, sm in zip(cells, ["AOne", "ATwo", "AThree"]):
            pct, k, n = re.match(r"([\d.]+) \((\d+)/(\d+)\)", cell).groups()
            assert pct == mac[f"Partc{sm}{tag}HarmPct"]
            assert f"{100.0 * int(k) / int(n):.1f}" == pct
            assert int(n) == 2304   # clean set (a7d + a7e + P1 pre-tool) is complete; the old P1 missing PPMF cell is archived
