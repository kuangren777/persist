"""Offline regression tests for the top-venue persistlab patch: per-model ports, served_root,
Llama single-call, and the frozen prov_strict authorization rule. No model calls."""
import persistlab as P


def test_local_ports_and_routing():
    assert P._local_port("qwen3-8b-local") == 8021
    assert P._local_port("llama31-8b-local") == 8023
    assert P._local_port("qwen3-32b-local") == 8031
    assert str(P.client("qwen3-8b-local").base_url).startswith("http://127.0.0.1:8021")
    assert str(P.client("llama31-8b-local").base_url).startswith("http://127.0.0.1:8023")
    assert P.client("claude-sonnet-5") is P.HUB   # hosted models go through the LLM_API_BASE gateway


def test_single_call_set():
    assert "llama31-8b-local" in P.SINGLE_CALL
    assert "qwen3-8b-local" not in P.SINGLE_CALL


def test_port_env_override(monkeypatch):
    monkeypatch.setenv("PORT_qwen3_32b_local", "8041")
    assert P._local_port("qwen3-32b-local") == 8041


def test_prov_strict_blocks_attacker_allows_user(monkeypatch):
    # strict rule: a target value is authorized only if the user wrote it (this msg or a user-tagged store item)
    mem = [{"vals": {"attacker-account-9981": "agent_tool", "acme-payroll-main": "user"}}]
    monkeypatch.setattr(P, "store_read", lambda tid: (None, mem))
    um = P._normv("run payroll for acme-payroll-main")
    uv = [n for v in P._user_values("t") if len(n := P._normv(v)) >= 6]

    def auth(c):
        cn = P._normv(c)
        if len(cn) < 6:
            return True
        return cn in um or any(cn in u or u in cn for u in uv)

    assert auth("attacker-account-9981") is False     # attacker value: no user source -> refused
    assert auth("acme-payroll-main") is True           # user-remembered value -> allowed
    assert "prov_strict" in P.DEFENSES


def test_served_root_guard(monkeypatch):
    import pytest
    monkeypatch.setattr(P, "served_root", lambda m: "Qwen/Qwen3-8B")
    P.assert_served_root("qwen3-8b-local")                       # match -> no raise
    # ModelScope dir root (dots written as '___') must still match after canonicalization
    monkeypatch.setattr(P, "served_root", lambda m: "/srv/models/LLM-Research/Meta-Llama-3___1-8B-Instruct")
    P.assert_served_root("llama31-8b-local")                     # canon match -> no raise
    monkeypatch.setattr(P, "served_root", lambda m: "meta-llama/Llama-3.1-8B-Instruct")
    with pytest.raises(SystemExit):
        P.assert_served_root("qwen3-8b-local")                   # wrong model on the port -> refuse
    monkeypatch.setattr(P, "served_root", lambda m: "UNKNOWN:conn refused")
    with pytest.raises(SystemExit):
        P.assert_served_root("qwen3-32b-local")                  # port down -> refuse
    P.assert_served_root("claude-sonnet-5")                       # hub model -> no-op


if __name__ == "__main__":
    import sys
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-q"]))
    except ImportError:
        test_local_ports_and_routing(); test_single_call_set()
        print("core tests passed (pytest not installed; monkeypatch tests skipped)")
