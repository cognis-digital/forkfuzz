"""Smoke tests for FORKFUZZ. No network, stdlib + pytest only."""

import json
import os

import pytest

from forkfuzz import (
    TOOL_NAME,
    TOOL_VERSION,
    fuzz,
    load_spec,
    parse_spec,
    run_sequence,
    safe_eval,
)
from forkfuzz.core import Call, SpecError
from forkfuzz.cli import main

DEMO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demos",
    "01-basic",
    "vault.json",
)


def test_metadata():
    assert TOOL_NAME == "forkfuzz"
    assert TOOL_VERSION.count(".") == 2


def test_safe_eval_basics():
    assert safe_eval("a + b * 2", {"a": 1, "b": 3}) == 7
    assert safe_eval("x >= 0 and y >= 0", {"x": 1, "y": 0}) is True
    assert safe_eval("total == alice + bob", {"total": 5, "alice": 2, "bob": 3}) is True
    assert safe_eval("max(a, b)", {"a": 4, "b": 9}) == 9


def test_safe_eval_rejects_unsafe():
    with pytest.raises(SpecError):
        safe_eval("__import__('os').system('echo hi')", {})
    with pytest.raises(SpecError):
        safe_eval("open('x')", {})
    with pytest.raises(SpecError):
        safe_eval("unknown_name + 1", {})


def test_demo_finds_violation():
    spec = load_spec(DEMO)
    report = fuzz(spec, runs=500, seq_len=20, seed=0)
    assert report.failed, "the buggy vault must produce a finding"
    names = {f.invariant for f in report.findings}
    # The planted bug drives a balance negative and/or breaks solvency.
    assert names & {"non_negative", "solvent"}
    # Counterexample must actually reproduce the violation when replayed.
    f = report.findings[0]
    _, violated, _ = run_sequence(spec, f.sequence)
    assert violated is not None and violated.name == f.invariant


def test_shrink_produces_minimal_counterexample():
    spec = load_spec(DEMO)
    report = fuzz(spec, runs=500, seq_len=30, seed=3)
    assert report.failed
    # A single oversized transfer from a zero balance is enough; shrinking
    # should reduce the counterexample to a very short sequence.
    assert len(report.findings[0].sequence) <= 3


def test_passing_spec_reports_clean():
    safe_spec = parse_spec(
        {
            "name": "Counter",
            "state": {"n": 0},
            "functions": [
                {
                    "name": "inc",
                    "args": [{"name": "k", "type": "int", "min": 1, "max": 5}],
                    "guard": "k > 0",
                    "effects": {"n": "n + k"},
                }
            ],
            "invariants": [{"name": "monotone", "expr": "n >= 0"}],
        }
    )
    report = fuzz(safe_spec, runs=200, seq_len=15, seed=1)
    assert not report.failed
    assert report.calls_executed > 0


def test_initial_state_violation_is_caught():
    spec = parse_spec(
        {
            "name": "BornBroken",
            "state": {"x": -1},
            "functions": [{"name": "noop", "effects": {}}],
            "invariants": [{"name": "pos", "expr": "x >= 0"}],
        }
    )
    report = fuzz(spec, runs=10, seq_len=5, seed=0)
    assert report.failed
    assert report.findings[0].sequence == []


def test_run_sequence_unknown_func_raises():
    spec = load_spec(DEMO)
    with pytest.raises(SpecError):
        run_sequence(spec, [Call(func="does_not_exist", args={})])


def test_parse_spec_rejects_unknown_effect_target():
    with pytest.raises(SpecError):
        parse_spec(
            {
                "name": "bad",
                "state": {"a": 0},
                "functions": [{"name": "f", "effects": {"b": "1"}}],
                "invariants": ["a >= 0"],
            }
        )


def test_cli_table_exit_code(capsys):
    rc = main(["check", DEMO])
    out = capsys.readouterr().out
    assert rc == 1  # findings -> non-zero for CI gates
    assert "FAIL" in out
    assert "BROKEN" in out


def test_cli_json_is_valid(capsys):
    rc = main(["check", DEMO, "--format", "json"])
    out = capsys.readouterr().out
    assert rc == 1
    payload = json.loads(out)
    assert payload["tool"] == "forkfuzz"
    assert payload["passed"] is False
    assert payload["findings"]
    assert "counterexample" in payload["findings"][0]


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "forkfuzz" in out
