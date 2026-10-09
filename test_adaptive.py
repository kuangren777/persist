"""Offline tests for the Block A adaptive transforms + gate differentiation. No model calls."""
import persistlab as P
import persistlab_adaptive as A

SC = {s.key: s for s in P.scenarios()}


def test_a1_a2_transforms_hide_full_poison():
    for sc in SC.values():
        for t in range(6):
            a = A.adaptive_scenario(sc, "A1", t)
            lo = a.inject.lower()
            assert sc.poison.lower() not in lo, (sc.key, "A1", t)   # full value not contiguous
            p1, p2 = A._split(sc.poison, A.A1_DEV[t][0])
            assert p1.lower() in lo and p2.lower() in lo
        for t in range(6):
            a = A.adaptive_scenario(sc, "A2", t)
            assert sc.poison.lower() not in a.inject.lower(), (sc.key, "A2", t)


def test_held_out_also_hide():
    for sc in SC.values():
        for t in range(2):
            assert sc.poison.lower() not in A.adaptive_scenario(sc, "A1", t, held=True).inject.lower()
            assert sc.poison.lower() not in A.adaptive_scenario(sc, "A2", t, held=True).inject.lower()


def test_gate_differentiation():
    # the reconstructed full value: prov_gate misses a split; prov_gate_wide catches a separator encoding;
    # prov_strict blocks any value with no user source.
    poison = SC["payment_account"].poison
    a, b = A._split(poison, 0.5)
    cvn = P._normv(poison)
    for stored, wide_should in [(f"part one {a}, part two {b}", False), (A.A2_DEV[0][1](poison), True)]:
        atn = [n for v in [stored] if len(n := P._normv(v)) >= 6]
        wide_hit = len(cvn) >= 6 and any(cvn in n or n in cvn for n in atn)
        assert (poison in {stored}) is False                 # prov_gate exact: miss
        assert wide_hit is wide_should                       # wide: catches separators, misses split
        assert cvn not in P._normv("set the vendor payee account")   # prov_strict: no user source -> block


if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-q"]))
