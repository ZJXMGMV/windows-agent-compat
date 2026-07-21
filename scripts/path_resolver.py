#!/usr/bin/env python3
"""Path Resolver for the Windows Agent Runtime.

Normalizes diverse path notations into a canonical absolute Windows path so
the agent never has to reason about separators or prefixes itself.

Supported inputs:
- Relative:  ``foo/bar``  ``./x``  ``../y``
- Home:      ``~/Documents``  ``~\\.config``
- Drive:     ``C:\\x``  ``C:/x``
- UNC:       ``\\\\server\\share\\x``
- WSL mount: ``/mnt/c/Users/x``  →  ``C:\\Users\\x``
- Long path: ``\\\\?\\C:\\very\\long`` (passthrough)
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


# /mnt/<drive>/...  →  <drive>:\...
_WSL_MOUNT = re.compile(r"^/mnt/([a-z])/(.*)$", re.IGNORECASE)
# //server/share/... (forward-slash UNC)
_SLASH_UNC = re.compile(r"^//([^/]+)/([^/]+)/(.*)$")
# \\server\share\... (backslash UNC)
_BSLASH_UNC = re.compile(r"^\\\\([^\\]+)\\([^\\]+)\\(.*)$")


class PathResolver:
    """Resolve any supported path notation to a canonical absolute path."""

    def __init__(self, cwd: str | None = None, home: str | None = None) -> None:
        self._cwd = Path(cwd) if cwd else Path(os.getcwd())
        self._home = Path(home) if home else Path(os.path.expanduser("~"))

    def resolve(self, raw: str) -> str:
        """Return a canonical absolute Windows path string.

        Raises ValueError only for truly malformed input (empty string).
        """
        if not raw or not raw.strip():
            raise ValueError("empty path")

        s = raw.strip()

        # Long-path prefix passthrough
        if s.startswith("\\\\?\\"):
            return s

        # UNC (backslash)
        m = _BSLASH_UNC.match(s)
        if m:
            rest = m.group(3).replace('/', '\\')
            return f"\\\\{m.group(1)}\\{m.group(2)}\\{rest}"

        # UNC (forward slash)
        m = _SLASH_UNC.match(s)
        if m:
            rest = m.group(3).replace('/', '\\')
            return f"\\\\{m.group(1)}\\{m.group(2)}\\{rest}"

        # WSL mount /mnt/c/...
        m = _WSL_MOUNT.match(s)
        if m:
            drive = m.group(1).upper() + ":"
            rest = m.group(2).replace("/", "\\")
            return f"{drive}\\{rest}" if rest else f"{drive}\\"

        # Home ~
        if s == "~" or s.startswith("~/") or s.startswith("~\\"):
            tail = s[1:].lstrip("/\\")
            return str(self._home / tail) if tail else str(self._home)

        # Double-slash collapse (e.g. "a//b")
        collapsed = re.sub(r"[/\\]+", "\\\\", s)

        # Absolute drive path
        if re.match(r"^[A-Za-z]:", collapsed):
            return str(Path(collapsed).resolve())

        # Relative path
        return str((self._cwd / collapsed).resolve())

    def normalize(self, raw: str) -> str:
        """Loose normalization: separators + backslash, no absolutization."""
        return raw.replace("/", "\\")


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("Usage: path_resolver.py <path>")
        return 1
    try:
        print(PathResolver().resolve(sys.argv[1]))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
