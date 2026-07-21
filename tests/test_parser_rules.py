#!/usr/bin/env python3
"""Self-test harness for the pure deterministic string layers.

Covers two modules that have no host-state dependency and are therefore fully
testable in isolation:

  - path_resolver.py : notation normalization (~ / .. / //UNC / \\\\server /
    /mnt/c WSL mount / mixed separators / \\\\?\\ long-path passthrough).
    Historically a source of f-string-backslash bugs, so exact-output
    regression matters. cwd/home are pinned in the fixture for host-independence.
  - output_parser.py : the ok gate (exit code + fatal-keyword scan) and error
    classification. Guards against fatal-keyword false positives/negatives.

Data-driven over tests/parser_fixtures.json. Exit 0 = green, 1 = failure.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from path_resolver import PathResolver  # noqa: E402
from output_parser import OutputParser  # noqa: E402

FIXTURES = os.path.join(HERE, "parser_fixtures.json")


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


def test_path_resolver(fx: dict, r: Results) -> None:
    spec = fx["path_resolver"]
    pr = PathResolver(cwd=spec["cwd"], home=spec["home"])
    for c in spec["cases"]:
        got = pr.resolve(c["in"])
        if got == c["out"]:
            r.ok()
        else:
            r.fail(f"PATH {c['in']!r}: expected {c['out']!r} got {got!r}")
    for bad in spec.get("raises", []):
        try:
            pr.resolve(bad)
            r.fail(f"PATH {bad!r}: expected ValueError, none raised")
        except ValueError:
            r.ok()
        except Exception as exc:  # noqa: BLE001
            r.fail(f"PATH {bad!r}: expected ValueError, got {type(exc).__name__}")


def test_output_parser(fx: dict, r: Results) -> None:
    for c in fx["output_parser"]["cases"]:
        res = OutputParser(error=c["stderr"], exit_code=c["exit_code"]).parse()
        if res["ok"] != c["ok"]:
            r.fail(f"PARSE ok {c['stderr']!r} ec={c['exit_code']}: expected ok={c['ok']} got {res['ok']}")
        elif sorted(res["errors"]) != sorted(c["errors"]):
            r.fail(f"PARSE errors {c['stderr']!r}: expected {c['errors']} got {res['errors']}")
        else:
            r.ok()


def main() -> int:
    with open(FIXTURES, encoding="utf-8") as f:
        fx = json.load(f)

    r = Results()
    test_path_resolver(fx, r)
    test_output_parser(fx, r)

    print(f"Parser/path harness: {r.passed} passed, {r.failed} failed")
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
