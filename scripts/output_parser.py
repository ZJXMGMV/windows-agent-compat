#!/usr/bin/env python3
"""Output parser for Windows command results.

Normalizes stdout/stderr, handles PowerShell object output, and classifies
common Windows errors.
"""
from __future__ import annotations

import re
from typing import Any


class OutputParser:
    """Parse and normalize shell output."""

    ERROR_PATTERNS = {
        "permission_denied": re.compile(r"访问被拒绝|Permission denied|Access is denied", re.IGNORECASE),
        "command_not_found": re.compile(r"无法将|不是内部或外部命令|not recognized as an internal or external command|command not found", re.IGNORECASE),
        "path_not_found": re.compile(r"找不到路径|找不到文件|无法找到路径|The system cannot find the (path|file)", re.IGNORECASE),
        "syntax_error": re.compile(r"命令语法不正确|syntax error", re.IGNORECASE),
    }

    def __init__(self, output: str = "", error: str = "", exit_code: int = 0) -> None:
        self.stdout = output
        self.stderr = error
        self.exit_code = exit_code

    def parse(self) -> dict[str, Any]:
        stdout = self._stringify(self.stdout)
        stderr = self._stringify(self.stderr)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": self.exit_code,
            "ok": self.exit_code == 0 and not self._is_fatal_stderr(stderr),
            "errors": self._classify_errors(stderr),
        }

    def _stringify(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value)

    def _is_fatal_stderr(self, stderr: str) -> bool:
        # Some PowerShell commands write warnings to stderr but exit 0.
        fatal_keywords = ["error", "失败", "exception", "terminated"]
        return any(kw in stderr.lower() for kw in fatal_keywords)

    def _classify_errors(self, stderr: str) -> list[str]:
        errors = []
        for name, pattern in self.ERROR_PATTERNS.items():
            if pattern.search(stderr):
                errors.append(name)
        return errors


def main() -> int:
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: output_parser.py '<stderr>' [exit_code]")
        return 1

    stderr = sys.argv[1]
    exit_code = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    parser = OutputParser(error=stderr, exit_code=exit_code)
    print(json.dumps(parser.parse(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
