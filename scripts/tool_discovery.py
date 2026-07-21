#!/usr/bin/env python3
"""Tool Discovery for the Windows Agent Runtime.

Resolves a logical tool name (e.g. ``git``, ``python``) to the best concrete
executable among multiple Windows candidates, so the agent never has to guess
which of ``git.exe`` / ``git.cmd`` / ``git.ps1`` / ``python`` / ``python3`` /
``py`` is present and preferred.

Priority rules:
- Prefer real ``.exe`` over ``.cmd`` / ``.bat`` / ``.ps1`` wrappers.
- Prefer the first match in the candidate list order.
- Exclude QClaw's ``bash.cmd``/``bash.bat`` false positives.
"""
from __future__ import annotations

import os
import shutil
from typing import Any


# Logical name → ordered candidate base names (without extension)
_TOOL_CANDIDATES: dict[str, list[str]] = {
    "git": ["git"],
    "python": ["python", "python3", "py"],
    "node": ["node"],
    "npm": ["npm", "npm.cmd"],
    "uv": ["uv", "uv.exe"],
    "cargo": ["cargo"],
    "go": ["go"],
    "java": ["java"],
    "docker": ["docker", "docker.exe"],
    "bash": ["bash"],
    "pwsh": ["pwsh", "pwsh.exe"],
    "powershell": ["powershell", "powershell.exe"],
}


# Extensions ordered by preference (real exe wins over script wrappers)
_EXT_PRIORITY = [".exe", "", ".cmd", ".bat", ".ps1"]


_EXCLUDE_SUFFIXES = ("bash.cmd", "bash.bat")


class ToolDiscovery:
    """Resolve logical tool names to best available executables."""

    def __init__(self, path_env: str | None = None) -> None:
        self._path_env = path_env

    def resolve(self, tool: str) -> dict[str, Any]:
        """Return discovery info for a logical tool name."""
        candidates = _TOOL_CANDIDATES.get(tool, [tool])
        found: list[dict[str, str]] = []
        for cand in candidates:
            for ext in _EXT_PRIORITY:
                name = cand + ext
                if name.lower().endswith(_EXCLUDE_SUFFIXES):
                    continue
                path = shutil.which(name, path=self._path_env)
                if path:
                    found.append({
                        "name": name,
                        "path": path,
                        "ext": ext or "(none)",
                    })
                    break  # first ext match per candidate wins
        return {
            "tool": tool,
            "resolved": found[0]["path"] if found else None,
            "candidates_found": found,
            "available": bool(found),
        }

    def discover_all(self, tools: list[str] | None = None) -> dict[str, dict[str, Any]]:
        target = tools or list(_TOOL_CANDIDATES.keys())
        return {t: self.resolve(t) for t in target}


def main() -> int:
    import json
    import sys

    tools = sys.argv[1:] or list(_TOOL_CANDIDATES.keys())
    td = ToolDiscovery()
    result = td.discover_all(tools)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
