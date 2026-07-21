#!/usr/bin/env python3
"""Recovery Engine for the Windows Agent Runtime.

Takes an ExecRunner result (the post-execution JSON dict) and:
1. Classifies the error category.
2. Produces human-readable recovery *suggestions* an agent can follow.
3. Optionally produces *auto-recovery actions* — self-contained (shell, cwd,
   timeout) tuples that the ExecRunner can retry automatically.

Design principle: recovery actions must be *deterministic and narrow* — no AI
guessing, no LLM fallback for the recovery itself.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Recovery data types
# ---------------------------------------------------------------------------

class RecoveryAction:
    """A self-contained recovery attempt."""

    __slots__ = ("name", "command", "shell", "cwd", "timeout")

    def __init__(
        self,
        name: str,
        command: str,
        shell: str | None = None,
        cwd: str | None = None,
        timeout: int = 15,
    ) -> None:
        self.name = name
        self.command = command
        self.shell = shell
        self.cwd = cwd
        self.timeout = timeout


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

RecoveryRule = tuple[
    str,                       # error_category
    re.Pattern,                # stderr pattern
    str,                       # template / hint
    Callable[[dict, dict | None], RecoveryAction | None] | None,  # auto-recovery builder
]

_RECOVERY_RULES: list[RecoveryRule] = []


def _register(
    category: str,
    pattern: str,
    hint: str,
    auto_recovery: Callable[[dict, dict | None], RecoveryAction | None] | None = None,
) -> None:
    _RECOVERY_RULES.append((category, re.compile(pattern, re.IGNORECASE), hint, auto_recovery))


# ---------------------------------------------------------------------------
# Auto-recovery builders
# ---------------------------------------------------------------------------

def _find_exe_and_retry(parsed: dict, env: dict | None) -> RecoveryAction | None:
    """If a command name can be extracted from the original command, try `where.exe` + retry with full path."""
    original = parsed.get("original", "")
    fallback = parsed.get("fallback", False)
    # Only act when the command fell through untranslated → best guess is command-not-found
    if not fallback:
        return None
    first_word = original.strip().split()[0] if original.strip() else ""
    if not first_word:
        return None
    # Try where.exe
    try:
        proc = subprocess.run(
            ["where.exe", first_word],
            capture_output=True, timeout=5, encoding="utf-8", errors="replace",
        )
        if proc.returncode == 0:
            full_paths = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
            if full_paths:
                # Rewrite command using the first found path
                fixed = original.replace(first_word, full_paths[0], 1)
                shell_used = parsed.get("shell_used", "pwsh")
                return RecoveryAction(
                    name=f"resolve_{first_word}",
                    command=fixed,
                    shell=shell_used,
                    timeout=30,
                )
    except Exception:  # noqa: BLE001
        pass
    return None


def _try_gbk_redecode(parsed: dict, env: dict | None) -> RecoveryAction | None:
    """If a command printed GBK mojibake, re-run with explicit codepage fallback (cmd)."""
    stdout = parsed.get("stdout", "")
    stderr = parsed.get("stderr", "")
    # Detect typical GBK-mojibake glyphs in Latin-1 ranges
    mojibake_chars = {"\u00e4", "\u00e5", "\u00e6", "\u00b1", "\u00d7", "\u00f7"}
    if any(c in stdout + stderr for c in mojibake_chars):
        original = parsed.get("original", "")
        if original:
            return RecoveryAction(
                name="gbk_fallback",
                command=original,
                shell="cmd",  # cmd.exe with chcp 936
                timeout=30,
            )
    return None


def _try_python_module_path(parsed: dict, env: dict | None) -> RecoveryAction | None:
    """If a python command was not found, try `py -3` or explicit `python3`."""
    original = parsed.get("original", "")
    stderr = parsed.get("stderr", "")
    if "python" in original.lower() and ("无法将" in stderr or "not recognized" in stderr):
        return RecoveryAction(
            name="python_fallback",
            command=original.replace("python", "python3", 1),
            shell=parsed.get("shell_used", "pwsh"),
            timeout=30,
        )
    return None


# ---------------------------------------------------------------------------
# Register all recovery rules
# ---------------------------------------------------------------------------

_register(
    "command_not_found",
    r"无法将|不是内部或外部命令|not recognized as an internal or external command|not recognized as a name of a cmdlet|is not recognized as|command not found",
    "Command not found. Try: `where.exe <tool>` or `Get-Command <tool>` to locate the executable.",
    auto_recovery=_find_exe_and_retry,
)

_register(
    "permission_denied",
    r"访问被拒绝|Permission denied|Access is denied",
    "Permission denied. Possible fixes: run as Administrator, close file in another process, "
    "or check file/directory ACL with `icacls <path>`.",
)

_register(
    "path_not_found",
    r"找不到路径|找不到文件|无法找到路径|The system cannot find the (path|file)",
    "Path does not exist. Verify with `Test-Path` or `dir` before retrying.",
)

_register(
    "syntax_error",
    r"命令语法不正确|syntax error",
    "Syntax error. The translated command may have quoting issues. Try wrapping paths in double quotes.",
)

_register(
    "encoding_mojibake",
    r"",
    "Output contains mojibake characters. The encoding fallback chain may have mismatched.",
    auto_recovery=_try_gbk_redecode,
)

_register(
    "file_in_use",
    r"正在被另一进程使用|The process cannot access the file because it is being used by another process|File in use|being used by another",
    "File is locked by another process. Try closing: Chrome, VSCode, Notepad++, or the app that opened it.",
)

_register(
    "python_not_found",
    r"python.*(无法将|not recognized|not found)",
    "Python not in PATH. Try `py -3` or `python3` instead.",
    auto_recovery=_try_python_module_path,
)

_register(
    "git_not_available",
    r"git.*(无法将|not recognized|not found)",
    "Git not in PATH. Use Runtime's native `wrap` operations (copy/move/write/read) instead of git commands.",
)

_register(
    "timeout_or_hung",
    r"",
    "Command timed out or hung. Possible fixes: reduce input size, check for interactive prompts, "
    "or break long-running commands into smaller steps.",
)

_register(
    "admin_required",
    r"需要管理员权限|administrator privilege|required privilege|Run as administrator",
    "Administrator access required. Re-run the agent from an elevated terminal or use `Start-Process -Verb RunAs`.",
)


# ---------------------------------------------------------------------------
# Recovery Engine
# ---------------------------------------------------------------------------

class RecoveryEngine:
    """Classify errors from an ExecRunner result and produce recovery suggestions + auto-actions."""

    def __init__(self, env: dict[str, Any] | None = None) -> None:
        self._env = env  # cached EnvDetect().detect() result, optional

    def analyze(self, result: dict[str, Any]) -> dict[str, Any]:
        """Analyze an ExecRunner result dict and return recovery info.

        Returns:
        {
            "ok": bool,
            "suggestions": [RecoverySuggestion dicts...],
            "auto_recovery": RecoveryAction dict | None,
        }
        """
        if result.get("ok", False):
            return {"ok": True, "suggestions": [], "auto_recovery": None}

        stderr = result.get("stderr", "")
        suggestions: list[dict] = []
        auto_action: RecoveryAction | None = None

        for category, pattern, hint, auto_builder in _RECOVERY_RULES:
            # Special-cased rules that don't rely on stderr pattern matching
            if category == "encoding_mojibake":
                auto_action_candidate = _try_gbk_redecode(result, self._env)
                if auto_action_candidate:
                    auto_action = auto_action_candidate
                    suggestions.append({
                        "category": category,
                        "severity": "medium",
                        "message": "Output appears to contain encoding artifacts (mojibake).",
                        "fix_hint": hint,
                    })
                continue

            if category == "timeout_or_hung":
                if result.get("exit_code") == -1:
                    suggestions.append({
                        "category": category,
                        "severity": "high",
                        "message": "Command timed out or did not produce output.",
                        "fix_hint": hint,
                    })
                continue

            if not pattern.search(stderr):
                continue

            severity = "high" if category in ("command_not_found", "admin_required") else "medium"
            suggestions.append({
                "category": category,
                "severity": severity,
                "message": hint.split(".")[0] if "." in hint else hint,
                "fix_hint": hint,
            })

            if auto_builder:
                auto_action_candidate = auto_builder(result, self._env)
                if auto_action_candidate:
                    auto_action = auto_action_candidate

        return {
            "ok": False,
            "suggestions": suggestions,
            "auto_recovery": {
                "name": auto_action.name,
                "command": auto_action.command,
                "shell": auto_action.shell,
                "cwd": auto_action.cwd,
                "timeout": auto_action.timeout,
            } if auto_action else None,
        }


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main() -> int:
    import io

    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

    if len(sys.argv) < 2:
        print("Usage: recovery.py '<exec_result_json>'")
        return 1

    try:
        exec_result = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print("Error: first argument must be a JSON string", file=sys.stderr)
        return 1

    engine = RecoveryEngine()
    print(json.dumps(engine.analyze(exec_result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
