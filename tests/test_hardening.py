"""Hardening tests: input validation, error paths, and edge cases."""

from __future__ import annotations

import pytest

from forkfuzz.core import Call, SpecError, fuzz, parse_spec, run_sequence
from forkfuzz.cli import main

# ---------------------------------------------------------------------------
# parse_spec: Arg validation
# ---------------------------------------------------------------------------


def test_parse_spec_rejects_unknown_arg_type():
    """An unsupported arg type raises SpecError with a clear message."""
    with pytest.raises(SpecError, match="unsupported type"):
        parse_spec(
            {
                "name": "bad_type",
                "state": {"x": 0},
                "functions": [
                    {
                        "name": "f",
                        "args": [{"name": "v", "type": "string"}],
                        "effects": {},
                    }
                ],
                "invariants": ["x >= 0"],
            }
        )


def test_parse_spec_rejects_min_greater_than_max():
    """An arg with min > max raises SpecError."""
    with pytest.raises(SpecError, match="min.*max"):
        parse_spec(
            {
                "name": "bad_range",
                "state": {"x": 0},
                "functions": [
                    {
                        "name": "f",
                        "args": [{"name": "v", "type": "int", "min": 10, "max": 5}],
                        "effects": {},
                    }
                ],
                "invariants": ["x >= 0"],
            }
        )


def test_parse_spec_rejects_empty_choices():
    """An arg with an empty choices list raises SpecError."""
    with pytest.raises(SpecError, match="choices.*non-empty"):
        parse_spec(
            {
                "name": "empty_choices",
                "state": {"x": 0},
                "functions": [
                    {
                        "name": "f",
                        "args": [{"name": "v", "type": "int", "choices": []}],
                        "effects": {},
                    }
                ],
                "invariants": ["x >= 0"],
            }
        )


def test_parse_spec_rejects_non_numeric_min():
    """An arg with a string 'min' raises SpecError."""
    with pytest.raises(SpecError, match="'min' must be a number"):
        parse_spec(
            {
                "name": "bad_min",
                "state": {"x": 0},
                "functions": [
                    {
                        "name": "f",
                        "args": [{"name": "v", "type": "int", "min": "zero"}],
                        "effects": {},
                    }
                ],
                "invariants": ["x >= 0"],
            }
        )


# ---------------------------------------------------------------------------
# fuzz(): parameter range guard
# ---------------------------------------------------------------------------


def _trivial_spec():
    return parse_spec(
        {
            "name": "trivial",
            "state": {"n": 0},
            "functions": [{"name": "noop", "effects": {}}],
            "invariants": ["n >= 0"],
        }
    )


def test_fuzz_rejects_zero_runs():
    """fuzz() with runs=0 raises SpecError."""
    with pytest.raises(SpecError, match="runs.*>= 1"):
        fuzz(_trivial_spec(), runs=0)


def test_fuzz_rejects_negative_seq_len():
    """fuzz() with seq_len=-1 raises SpecError."""
    with pytest.raises(SpecError, match="seq_len.*>= 1"):
        fuzz(_trivial_spec(), seq_len=-1)


# ---------------------------------------------------------------------------
# ZeroDivisionError in effect expressions: reverts, does not crash
# ---------------------------------------------------------------------------


def test_zero_division_in_effect_reverts_call():
    """A div-by-zero in an effect expression reverts the call instead of crashing."""
    spec = parse_spec(
        {
            "name": "div_effect",
            "state": {"x": 5, "y": 0},
            "functions": [{"name": "f", "effects": {"x": "x / y"}}],
            "invariants": ["x >= 0"],
        }
    )
    # Should complete without raising; the call reverts, state unchanged.
    state, violated, idx = run_sequence(spec, [Call(func="f", args={})])
    assert violated is None, "invariant should still hold after reverted call"
    assert state["x"] == 5, "state must be unchanged after a reverted effect"


def test_zero_division_in_effect_does_not_crash_fuzzer():
    """fuzz() handles a spec with div-by-zero effects without raising."""
    spec = parse_spec(
        {
            "name": "div_fuzz",
            "state": {"x": 10, "y": 0},
            "functions": [{"name": "f", "effects": {"x": "x / y"}}],
            "invariants": ["x >= 0"],
        }
    )
    report = fuzz(spec, runs=50, seq_len=5, seed=1)
    # No crash is the main assertion; the invariant should hold throughout.
    assert not report.failed


# ---------------------------------------------------------------------------
# CLI: missing file and invalid numeric args
# ---------------------------------------------------------------------------


def test_cli_missing_file_returns_exit_2(capsys):
    """CLI returns exit code 2 and a clear stderr message for a missing spec."""
    rc = main(["check", "no_such_file_xyz.json"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not found" in err


def test_cli_negative_runs_returns_exit_2(capsys):
    """CLI returns exit code 2 when --runs is negative."""
    rc = main(["check", "irrelevant.json", "--runs", "-1"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "--runs" in err


def test_cli_zero_seq_len_returns_exit_2(capsys):
    """CLI returns exit code 2 when --seq-len is 0."""
    rc = main(["check", "irrelevant.json", "--seq-len", "0"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "--seq-len" in err


def test_cli_malformed_json_returns_exit_2(capsys, tmp_path):
    """CLI returns exit code 2 with a clear error for a malformed JSON spec."""
    bad_spec = tmp_path / "bad.json"
    bad_spec.write_text("{not valid json", encoding="utf-8")
    rc = main(["check", str(bad_spec)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "invalid JSON" in err or "error" in err.lower()


# ---------------------------------------------------------------------------
# mcp_server: module imports without crashing
# ---------------------------------------------------------------------------


def test_mcp_server_imports_cleanly():
    """mcp_server module must be importable without raising ImportError."""
    import forkfuzz.mcp_server  # noqa: F401 — import is the test
