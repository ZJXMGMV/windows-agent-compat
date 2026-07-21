#!/usr/bin/env python3
"""Safe cross-platform wrappers for common file/shell operations.

Use these instead of generating shell commands when the operation is fragile or
error-prone across different Windows shells.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable


def safe_rm(path: str | Path) -> None:
    """Remove a file or directory recursively."""
    target = Path(path)
    if not target.exists():
        return
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    else:
        target.unlink(missing_ok=True)


def safe_mkdir(path: str | Path) -> Path:
    """Create a directory and all parents."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def safe_copy(src: str | Path, dst: str | Path) -> None:
    """Copy a file or directory recursively."""
    source = Path(src)
    dest = Path(dst)
    if source.is_dir():
        shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(source, dest)


def safe_move(src: str | Path, dst: str | Path) -> None:
    """Move a file or directory."""
    shutil.move(str(src), str(dst))


def safe_read(path: str | Path, encoding: str = "utf-8") -> str:
    """Read a text file robustly."""
    target = Path(path)
    try:
        return target.read_text(encoding=encoding, errors="replace")
    except UnicodeDecodeError:
        for enc in ("gbk", "cp1252"):
            try:
                return target.read_text(encoding=enc, errors="replace")
            except UnicodeDecodeError:
                continue
        raise


def safe_write(path: str | Path, content: str, encoding: str = "utf-8") -> None:
    """Write text to a file, creating parent directories as needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding, errors="replace")


def safe_grep(pattern: str, files: Iterable[str | Path], case_sensitive: bool = False) -> list[str]:
    """Grep-like search across files.

    ``files`` can be glob patterns (e.g. '*.py') or explicit paths.
    Patterns are expanded relative to cwd.
    """
    import glob as _glob

    if isinstance(files, (str, Path)):
        files = [str(files)]
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern, flags)
    matches: list[str] = []
    expanded_files: list[str] = []
    for f in files:
        if not isinstance(f, (str, Path)):
            continue
        fstr = os.path.normpath(str(f))
        if any(ch in fstr for ch in '*?[]'):
            try:
                # Use glob with root_dir to avoid scandir('.') permission issues on Windows
                import glob as _glob
                expanded_files.extend(
                    _glob.glob(fstr, recursive=True, root_dir=os.getcwd())
                )
            except (OSError, PermissionError):
                # Fallback: if cwd scan fails, try absolute resolution
                expanded_files.extend(_glob.glob(fstr, recursive=True))
        else:
            expanded_files.append(fstr)
    # Deduplicate while preserving order
    seen = set()
    for fp in expanded_files:
        if fp not in seen:
            seen.add(fp)
            text = safe_read(fp)
            for line_no, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append(f"{fp}:{line_no}:{line}")
    return matches


def safe_find(root: str | Path, pattern: str) -> list[str]:
    """Find files matching a glob pattern under a root."""
    root_path = Path(root)
    return [str(p) for p in root_path.rglob(pattern) if p.is_file()]


def safe_env(name: str, value: str | None = None) -> str | None:
    """Get or set an environment variable."""
    if value is None:
        return os.environ.get(name)
    os.environ[name] = value
    return value


def safe_path(path: str) -> str:
    """Return a normalized absolute path for the current OS."""
    return str(Path(path).expanduser().resolve())


OPERATIONS = {
    "rm": safe_rm,
    "mkdir": safe_mkdir,
    "copy": safe_copy,
    "move": safe_move,
    "read": safe_read,
    "write": safe_write,
    "grep": safe_grep,
    "find": safe_find,
    "env": safe_env,
    "path": safe_path,
}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: tool_wrap.py <operation> [args...]")
        print("Operations: " + ", ".join(OPERATIONS.keys()))
        return 1

    op = sys.argv[1]
    if op not in OPERATIONS:
        print(f"Unknown operation: {op}")
        return 1

    if op == "write":
        # Multi-line content cannot be passed reliably via CLI args (shell quoting
        # mangles newlines). Accept --from-file <path> to read content from a file.
        args = sys.argv[2:]
        content = ""
        target = None
        i = 0
        while i < len(args):
            if args[i] == "--from-file":
                content = Path(args[i + 1]).read_text(encoding="utf-8", errors="replace")
                i += 2
            else:
                if target is None:
                    target = args[i]
                i += 1
        if target is None:
            print("Error: write requires a target path", file=sys.stderr)
            return 1
        safe_write(target, content)
        return 0

    func = OPERATIONS[op]
    try:
        result = func(*sys.argv[2:])  # type: ignore[arg-type]
        if result is not None:
            print(result)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
