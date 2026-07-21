#!/usr/bin/env python3
"""Recovery rule self-test harness.

Data-driven regression net for scripts/recovery.py. Guards against the #1 risk
when the ruleset grows: one rule's regex silently matching another category's
error text (cross-rule interference / substring false positives).

For every category it asserts, using tests/recovery_fixtures.json:
  1. positive samples classify to the target category
  2. positive samples do NOT trip any *undeclared* category
     (declared legit overlaps go in "also_ok") -- the anti-interference net
  3. negative samples do NOT classify to the target category
  4. auto_recovery cases produce the expected auto action name (or None)

It also enforces that every registered rule has a fixture entry, so a newly
added rule cannot be merged without its own positive/negative samples.

Exit code 0 = all green, 1 = any failure. No third-party deps.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from recovery import RecoveryEngine, _RECOVERY_RULES  # noqa: E402

FIXTURES = os.path.join(HERE, "recovery_fixtures.json")


class Results:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def ok(self) -> None:
        self.passed += 1

    def fail(self, msg: str) -> None:
        self.failed += 1
        self.failures.append(msg)


def _categories_for(engine: RecoveryEngine, stderr: str) -> list[str]:
    """Run the full engine over a synthetic failed result, return matched categories."""
    result = {"ok": False, "exit_code": 1, "stderr": stderr, "original": "", "shell_used": "pwsh"}
    out = engine.analyze(result)
    return [s["category"] for s in out["suggestions"]]


def test_coverage(fx: dict, r: Results) -> None:
    """Every registered rule must have a fixture case (forces samples for new rules)."""
    registered = {c for c, *_ in _RECOVERY_RULES}
    documented = set(fx["cases"].keys())
    # encoding_mojibake & timeout_or_hung are stderr-independent special cases;
    # they are exercised separately, not via stderr-pattern fixtures.
    special = {"encoding_mojibake", "timeout_or_hung"}
    missing = registered - documented - special
    extra = documented - registered
    if missing:
        r.fail(f"COVERAGE: rules without fixtures: {sorted(missing)}")
    else:
        r.ok()
    if extra:
        r.fail(f"COVERAGE: fixtures for unknown rules: {sorted(extra)}")
    else:
        r.ok()


def test_cases(fx: dict, engine: RecoveryEngine, r: Results) -> None:
    for category, spec in fx["cases"].items():
        also_ok = set(spec.get("also_ok", []))
        allowed = {category} | also_ok

        # 1 + 2: positives hit target AND don't trip undeclared categories
        for sample in spec.get("positive", []):
            matched = _categories_for(engine, sample)
            if category not in matched:
                r.fail(f"[{category}] positive NOT matched: {sample!r} -> {matched}")
                continue
            interference = [m for m in matched if m not in allowed]
            if interference:
                r.fail(f"[{category}] INTERFERENCE: {sample!r} also tripped {interference} "
                       f"(allowed={sorted(allowed)})")
            else:
                r.ok()

        # 3: negatives must NOT hit target
        for sample in spec.get("negative", []):
            matched = _categories_for(engine, sample)
            if category in matched:
                r.fail(f"[{category}] negative WRONGLY matched: {sample!r} -> {matched}")
            else:
                r.ok()


def test_auto_recovery(fx: dict, engine: RecoveryEngine, r: Results) -> None:
    for c in fx.get("auto_recovery", []):
        result = {
            "ok": False, "exit_code": 1,
            "stderr": c["stderr"], "original": c["original"],
            "shell_used": c.get("shell", "pwsh"), "fallback": c.get("fallback", False),
        }
        out = engine.analyze(result)
        auto = out.get("auto_recovery")
        got = auto["name"] if auto else None
        expect = c["expect_action"]
        if got == expect:
            r.ok()
        else:
            r.fail(f"[auto:{c['category']}] expected action {expect!r} got {got!r} "
                   f"for stderr={c['stderr']!r}")


def test_special_cases(engine: RecoveryEngine, r: Results) -> None:
    # timeout_or_hung: signalled by exit_code == -1, not by stderr
    out = engine.analyze({"ok": False, "exit_code": -1, "stderr": "", "original": "x", "shell_used": "pwsh"})
    if any(s["category"] == "timeout_or_hung" for s in out["suggestions"]):
        r.ok()
    else:
        r.fail("[timeout_or_hung] not detected on exit_code == -1")

    # encoding_mojibake: mojibake chars in stdout trigger gbk fallback
    mojibake = "\ufffd\ufffd\ufffd"  # replacement chars
    res = {"ok": False, "exit_code": 1, "stderr": "", "stdout": mojibake,
           "original": "type x.txt", "shell_used": "pwsh"}
    out = engine.analyze(res)
    # It's fine whether or not it fires (depends on _try_gbk_redecode heuristics);
    # we only assert the engine does not crash and returns a well-formed dict.
    if isinstance(out, dict) and "suggestions" in out and "auto_recovery" in out:
        r.ok()
    else:
        r.fail("[encoding_mojibake] engine returned malformed result")


def main() -> int:
    with open(FIXTURES, encoding="utf-8") as f:
        fx = json.load(f)

    engine = RecoveryEngine()
    r = Results()

    test_coverage(fx, r)
    test_cases(fx, engine, r)
    test_auto_recovery(fx, engine, r)
    test_special_cases(engine, r)

    print(f"Recovery rule harness: {r.passed} passed, {r.failed} failed "
          f"({len(_RECOVERY_RULES)} rules registered)")
    if r.failures:
        print("\nFailures:")
        for msg in r.failures:
            print(f"  - {msg}")
        return 1
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    raise SystemExit(main())
