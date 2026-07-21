#!/usr/bin/env python3
"""Unified command execution with shell selection, encoding handling, and retries.

Returns a standard JSON result independent of the underlying shell.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from cmd_adapter import CommandTranslator


class ExecRunner:
    """Run commands on Windows with shell fallback and encoding handling."""

    SHELL_COMMANDS = {
        "pwsh": ["pwsh.exe", "-NoProfile", "-Command"],
        "powershell": ["powershell.exe", "-NoProfile", "-Command"],
        "cmd": ["cmd.exe", "/C"],
        "bash": ["bash.exe", "-c"],
    }

    def __init__(self, preferred_shell: str = "pwsh") -> None:
        self.preferred_shell = preferred_shell
        self.translator = CommandTranslator()

    def available_shells(self) -> list[str]:
        return [shell for shell, cmd in self.SHELL_COMMANDS.items() if self._find_shell(shell)]

    def _find_shell(self, shell: str) -> str | None:
        """Find a real shell executable, filtering out false positives like bash.CMD."""
        exe_name = self.SHELL_COMMANDS[shell][0]
        path = shutil.which(exe_name)
        if not path:
            return None
        # Filter out QClaw's bash.CMD wrapper — we want real bash.exe
        if shell == "bash":
            lower = path.lower()
            if lower.endswith("bash.cmd") or lower.endswith("bash.bat"):
                return None
        return path

    def select_shell(self, requested: str | None = None) -> str:
        if requested and requested in self.SHELL_COMMANDS:
            if self._find_shell(requested):
                return requested
        # Fallback chain
        for shell in ("pwsh", "powershell", "cmd", "bash"):
            if self._find_shell(shell):
                return shell
        raise RuntimeError("No supported shell found on this system")

    def run(
        self,
        cmd: str,
        shell: str | None = None,
        cwd: str | None = None,
        retries: int = 1,
        timeout: int = 30,
    ) -> dict[str, Any]:
        selected_shell = self.select_shell(shell)
        translated = self.translator.translate(cmd, shell=selected_shell)
        translated_cmd = translated["translated"]

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                result = self._execute(translated_cmd, selected_shell, cwd, timeout)
                result["translated_cmd"] = translated_cmd
                result["matched_rule"] = translated["matched_rule"]
                result["fallback"] = translated["fallback"]
                return result
            except (OSError, subprocess.TimeoutExpired) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(0.5)
                    continue
                break

        return {
            "ok": False,
            "stdout": "",
            "stderr": str(last_error) if last_error else "",
            "exit_code": -1,
            "shell_used": selected_shell,
            "translated_cmd": translated_cmd,
            "matched_rule": translated["matched_rule"],
            "fallback": translated["fallback"],
        }

    def _execute(self, cmd: str, shell: str, cwd: str | None, timeout: int) -> dict[str, Any]:
        base = self.SHELL_COMMANDS[shell]
        # Force UTF-8 output for PowerShell variants to avoid GBK encoding issues
        if shell in ("pwsh", "powershell"):
            prefix = (
                "chcp 65001 > $null; "
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                "$OutputEncoding = [System.Text.Encoding]::UTF8; "
                "$PSStyle.OutputRendering = 'PlainText'; "
            )
            full = base + [prefix + cmd]
        else:
            full = base + [cmd]
        proc = subprocess.run(
            full,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            encoding=None,  # raw bytes, decode manually for robustness
        )
        stdout = self._decode(proc.stdout)
        stderr = self._decode(proc.stderr)
        return {
            "ok": proc.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": proc.returncode,
            "shell_used": shell,
        }

    def _decode(self, data: bytes) -> str:
        if data is None:
            return ""
        # UTF-8 first (forced for PowerShell). Then GBK/cp1252 for Chinese Windows.
        # UTF-16 last: it can "successfully" decode GBK bytes into mojibake, so it
        # must only be a last resort for genuine UTF-16 (e.g. some WSL output).
        for enc in ("utf-8", "gbk", "cp1252", "utf-16"):
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("Usage: exec_runner.py <command> [shell=pwsh]")
        return 1

    cmd = sys.argv[1]
    shell = sys.argv[2] if len(sys.argv) > 2 else "pwsh"

    runner = ExecRunner(preferred_shell=shell)
    result = runner.run(cmd, shell=shell)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
