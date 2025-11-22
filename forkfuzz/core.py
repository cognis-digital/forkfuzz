"""Core engine for FORKFUZZ.

The engine evaluates a small, safe expression language (a restricted
subset of Python via the ``ast`` module) so that specs can express
guards, effects and invariants without ``eval`` of arbitrary code and
without any third-party dependency.

Design
------
* A *spec* defines named state variables, functions and invariants.
* Each function has optional ``args`` (typed parameters that the fuzzer
  generates values for), an optional ``guard`` (precondition -- if false
  the call is a no-op revert), and ``effects`` (assignments applied to
  the state).
* After every applied call the engine checks every invariant. The first
  invariant that evaluates falsy produces a counterexample.
* Failing sequences are shrunk (delta-debugging style) to the smallest
  prefix/subset that still violates an invariant.

Only the standard library is used.
"""

from __future__ import annotations

import ast
import json
import operator
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


class SpecError(ValueError):
    """Raised when a spec is malformed or an expression is unsafe."""


# --------------------------------------------------------------------------- #
# Safe expression evaluator
# --------------------------------------------------------------------------- #

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

_BOOL_OPS = {ast.And: all, ast.Or: any}

_UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Not: operator.not_,
}

# Builtins exposed inside expressions (pure, side-effect-free).
_SAFE_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "len": len,
    "int": int,
    "bool": bool,
    "sum": sum,
}


def safe_eval(expr: str, env: Dict[str, Any]) -> Any:
    """Evaluate a restricted expression ``expr`` against ``env``.

    Supported: numbers, booleans, ``None``, names (looked up in ``env``),
    arithmetic/comparison/boolean/unary operators, ternary ``a if c else
    b``, and a small set of pure builtin calls. Anything else raises
    :class:`SpecError`.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:  # pragma: no cover - defensive
        raise SpecError(f"cannot parse expression {expr!r}: {exc}") from exc
    return _eval_node(tree.body, env, expr)


def _eval_node(node: ast.AST, env: Dict[str, Any], expr: str) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        raise SpecError(f"unknown name {node.id!r} in expression {expr!r}")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise SpecError(f"unsupported operator in {expr!r}")
        return op(_eval_node(node.left, env, expr), _eval_node(node.right, env, expr))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise SpecError(f"unsupported unary operator in {expr!r}")
        return op(_eval_node(node.operand, env, expr))
    if isinstance(node, ast.BoolOp):
        fold = _BOOL_OPS[type(node.op)]
        return fold(_eval_node(v, env, expr) for v in node.values)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env, expr)
        for op_node, comparator in zip(node.ops, node.comparators):
            cmp = _CMP_OPS.get(type(op_node))
            if cmp is None:
                raise SpecError(f"unsupported comparison in {expr!r}")
            right = _eval_node(comparator, env, expr)
            if not cmp(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        cond = _eval_node(node.test, env, expr)
        return _eval_node(node.body if cond else node.orelse, env, expr)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCS:
            raise SpecError(f"disallowed call in expression {expr!r}")
        if node.keywords:
            raise SpecError(f"keyword args not allowed in {expr!r}")
        args = [_eval_node(a, env, expr) for a in node.args]
        return _SAFE_FUNCS[node.func.id](*args)
    raise SpecError(f"disallowed syntax {type(node).__name__} in expression {expr!r}")


# --------------------------------------------------------------------------- #
# Spec model
# --------------------------------------------------------------------------- #


@dataclass
class Arg:
    name: str
    type: str = "int"
    min: Optional[float] = None
    max: Optional[float] = None
    choices: Optional[List[Any]] = None


@dataclass
class Function:
    name: str
    args: List[Arg] = field(default_factory=list)
    guard: Optional[str] = None
    effects: Dict[str, str] = field(default_factory=dict)


@dataclass
class Invariant:
    name: str
    expr: str


@dataclass
class Spec:
    name: str
    state: Dict[str, Any]
    functions: List[Function]
    invariants: List[Invariant]

    def initial_state(self) -> Dict[str, Any]:
        return dict(self.state)


@dataclass
class Call:
    func: str
    args: Dict[str, Any]
    reverted: bool = False

    def as_text(self) -> str:
        inner = ", ".join(f"{k}={v!r}" for k, v in self.args.items())
        tail = "  [reverted]" if self.reverted else ""
        return f"{self.func}({inner}){tail}"


@dataclass
class Finding:
    invariant: str
    expr: str
    sequence: List[Call]
    state: Dict[str, Any]
    runs_executed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant": self.invariant,
            "expr": self.expr,
            "counterexample": [
                {"func": c.func, "args": c.args, "reverted": c.reverted}
                for c in self.sequence
            ],
            "counterexample_text": [c.as_text() for c in self.sequence],
            "final_state": self.state,
            "runs_executed": self.runs_executed,
        }


@dataclass
class Report:
    spec_name: str
    runs: int
    seq_len: int
    seed: int
    findings: List[Finding]
    calls_executed: int
    invariants_checked: int

    @property
    def failed(self) -> bool:
        return bool(self.findings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": "forkfuzz",
            "spec": self.spec_name,
            "runs": self.runs,
            "seq_len": self.seq_len,
            "seed": self.seed,
            "calls_executed": self.calls_executed,
            "invariants_checked": self.invariants_checked,
            "passed": not self.failed,
            "findings": [f.to_dict() for f in self.findings],
        }


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def parse_spec(data: Dict[str, Any]) -> Spec:
    """Build a :class:`Spec` from a decoded JSON dict."""
    if not isinstance(data, dict):
        raise SpecError("spec must be a JSON object")

    name = str(data.get("name", "contract"))

    state = data.get("state", {})
    if not isinstance(state, dict):
        raise SpecError("'state' must be an object of name -> initial value")
    state = dict(state)

    raw_funcs = data.get("functions", [])
    if not isinstance(raw_funcs, list) or not raw_funcs:
        raise SpecError("'functions' must be a non-empty list")
    functions: List[Function] = []
    for rf in raw_funcs:
        if not isinstance(rf, dict) or "name" not in rf:
            raise SpecError("each function needs a 'name'")
        args: List[Arg] = []
        for ra in rf.get("args", []) or []:
            if not isinstance(ra, dict) or "name" not in ra:
                raise SpecError(f"bad arg in function {rf['name']!r}")
            args.append(
                Arg(
                    name=str(ra["name"]),
                    type=str(ra.get("type", "int")),
                    min=ra.get("min"),
                    max=ra.get("max"),
                    choices=ra.get("choices"),
                )
            )
        effects = rf.get("effects", {}) or {}
        if not isinstance(effects, dict):
            raise SpecError(f"'effects' of {rf['name']!r} must be an object")
        for var in effects:
            if var not in state:
                raise SpecError(
                    f"function {rf['name']!r} assigns unknown state var {var!r}"
                )
        functions.append(
            Function(
                name=str(rf["name"]),
                args=args,
                guard=rf.get("guard"),
                effects={str(k): str(v) for k, v in effects.items()},
            )
        )

    raw_invs = data.get("invariants", [])
    if not isinstance(raw_invs, list) or not raw_invs:
        raise SpecError("'invariants' must be a non-empty list")
    invariants: List[Invariant] = []
    for i, ri in enumerate(raw_invs):
        if isinstance(ri, str):
            invariants.append(Invariant(name=f"inv_{i}", expr=ri))
        elif isinstance(ri, dict) and "expr" in ri:
            invariants.append(
                Invariant(name=str(ri.get("name", f"inv_{i}")), expr=str(ri["expr"]))
            )
        else:
            raise SpecError("each invariant must be a string or {name, expr}")

    return Spec(name=name, state=state, functions=functions, invariants=invariants)


def load_spec(path: str) -> Spec:
    """Load and parse a spec from a JSON file path."""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise SpecError(f"invalid JSON in {path}: {exc}") from exc
    return parse_spec(data)


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #


def _gen_arg(arg: Arg, rng: random.Random) -> Any:
    if arg.choices:
        return rng.choice(arg.choices)
    if arg.type == "bool":
        return rng.choice([True, False])
    lo = arg.min if arg.min is not None else 0
    hi = arg.max if arg.max is not None else 1000
    if arg.type == "float":
        return rng.uniform(lo, hi)
    # default int; bias toward boundaries to surface edge cases
    if rng.random() < 0.25:
        return rng.choice([int(lo), int(hi)])
    return rng.randint(int(lo), int(hi))


def _check_invariants(
    spec: Spec, state: Dict[str, Any]
) -> Optional[Invariant]:
    for inv in spec.invariants:
        try:
            ok = safe_eval(inv.expr, state)
        except ZeroDivisionError:
            # a div-by-zero inside an invariant counts as a violation
            return inv
        if not ok:
            return inv
    return None


def _apply_call(spec: Spec, func: Function, state: Dict[str, Any], call: Call) -> bool:
    """Apply a single call, returning True if it executed (guard passed)."""
    env = dict(state)
    env.update(call.args)
    if func.guard is not None:
        try:
            passed = safe_eval(func.guard, env)
        except ZeroDivisionError:
            passed = False
        if not passed:
            call.reverted = True
            return False
    # Evaluate every effect against the *pre* state (simultaneous update).
    new_values = {}
    for var, rhs in func.effects.items():
        new_values[var] = safe_eval(rhs, env)
    state.update(new_values)
    return True


def run_sequence(
    spec: Spec, sequence: Sequence[Call]
) -> Tuple[Dict[str, Any], Optional[Invariant], int]:
    """Replay a concrete ``sequence`` of calls.

    Returns ``(final_state, violated_invariant_or_None, index)`` where
    ``index`` is the call index at which the violation was detected (or
    ``len(sequence)`` if none).
    """
    by_name = {f.name: f for f in spec.functions}
    state = spec.initial_state()
    violated = _check_invariants(spec, state)
    if violated is not None:
        return state, violated, 0
    for i, call in enumerate(sequence):
        func = by_name.get(call.func)
        if func is None:
            raise SpecError(f"sequence references unknown function {call.func!r}")
        _apply_call(spec, func, state, call)
        violated = _check_invariants(spec, state)
        if violated is not None:
            return state, violated, i + 1
    return state, None, len(sequence)


def _shrink(
    spec: Spec, sequence: List[Call], violated: Invariant
) -> List[Call]:
    """Delta-debug a failing sequence to a minimal still-failing one."""
    seq = list(sequence)

    def still_fails(candidate: List[Call]) -> bool:
        _, v, _ = run_sequence(spec, candidate)
        return v is not None and v.name == violated.name

    # 1) shortest failing prefix
    lo, hi = 0, len(seq)
    while lo < hi:
        mid = (lo + hi) // 2
        if still_fails(seq[:mid]):
            hi = mid
        else:
            lo = mid + 1
    seq = seq[:lo] if lo <= len(seq) and still_fails(seq[:lo]) else seq

    # 2) greedily drop individual calls
    changed = True
    while changed:
        changed = False
        for i in range(len(seq)):
            candidate = seq[:i] + seq[i + 1 :]
            if candidate and still_fails(candidate):
                seq = candidate
                changed = True
                break
    return seq


def fuzz(
    spec: Spec,
    runs: int = 500,
    seq_len: int = 25,
    seed: int = 0,
    stop_on_first: bool = True,
) -> Report:
    """Fuzz ``spec`` with random call sequences.

    Generates up to ``runs`` sequences of length up to ``seq_len``. The
    first sequence that breaks an invariant is shrunk to a minimal
    counterexample and recorded. With ``stop_on_first=False`` the engine
    keeps searching for violations of *other* invariants too.
    """
    rng = random.Random(seed)
    findings: List[Finding] = []
    seen_invariants = set()
    calls_executed = 0

    # Catch invariants violated by the initial state immediately.
    init_state, init_violated, _ = run_sequence(spec, [])
    if init_violated is not None:
        findings.append(
            Finding(
                invariant=init_violated.name,
                expr=init_violated.expr,
                sequence=[],
                state=init_state,
                runs_executed=0,
            )
        )
        seen_invariants.add(init_violated.name)
        if stop_on_first:
            return Report(
                spec_name=spec.name,
                runs=runs,
                seq_len=seq_len,
                seed=seed,
                findings=findings,
                calls_executed=0,
                invariants_checked=len(spec.invariants),
            )

    for run_i in range(runs):
        length = rng.randint(1, max(1, seq_len))
        sequence: List[Call] = []
        for _ in range(length):
            func = rng.choice(spec.functions)
            args = {a.name: _gen_arg(a, rng) for a in func.args}
            sequence.append(Call(func=func.name, args=args))
        _, violated, idx = run_sequence(spec, sequence)
        calls_executed += idx
        if violated is None:
            continue
        if violated.name in seen_invariants:
            continue
        failing = sequence[:idx]
        minimal = _shrink(spec, failing, violated)
        final_state, _, _ = run_sequence(spec, minimal)
        findings.append(
            Finding(
                invariant=violated.name,
                expr=violated.expr,
                sequence=minimal,
                state=final_state,
                runs_executed=run_i + 1,
            )
        )
        seen_invariants.add(violated.name)
        if stop_on_first:
            break
        if len(seen_invariants) >= len(spec.invariants):
            break

    return Report(
        spec_name=spec.name,
        runs=runs,
        seq_len=seq_len,
        seed=seed,
        findings=findings,
        calls_executed=calls_executed,
        invariants_checked=len(spec.invariants),
    )
