#!/usr/bin/env python3
"""Generate an environment description block for agent system prompts.

The output is framework-agnostic: OpenClaw, Codex CLI, OpenCode, and Hermes
can inject it into their own system prompts.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from env_detect import EnvDetect

# Default template used if the external template file is missing
DEFAULT_TEMPLATE = """# Windows Environment
You are running on a Windows machine. Use the following rules when generating commands:

- OS: {os}
- Preferred shell: {preferred_shell}
- Path separator: {sep_char}
- Active codepage: {codepage}
- Long path support: {long_paths}
- Available tools: {tools}

Rules:
1. Prefer PowerShell 7 syntax if the command targets Windows.
2. Do NOT use Bash-only commands (rm -rf, chmod +x, export, grep, find) unless you are certain the environment is Git Bash/WSL.
3. For file operations, prefer the tool wrappers in this skill (`safe_rm`, `safe_mkdir`, etc.) instead of raw shell commands.
4. Always quote paths that contain spaces: `& "C:\\Program Files\\..."` for PowerShell, `"C:\\Program Files\\..."` for cmd.
5. Use `$env:NAME = value` for environment variables in PowerShell, not `export`.
"""

TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "prompt-template.txt"


def _load_template() -> str:
    """Load the prompt template from assets, falling back to the hardcoded default."""
    try:
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
        return text if text.strip() else DEFAULT_TEMPLATE
    except (OSError, ValueError):
        return DEFAULT_TEMPLATE


def generate_prompt(env: dict | None = None) -> str:
    if env is None:
        env = EnvDetect().detect()

    os_info = env.get("os", {})
    os_str = f"{os_info.get('system', 'Windows')} {os_info.get('release', '')} ({os_info.get('machine', '')})".strip()

    shell = env.get("shell", {})
    preferred = shell.get("preferred", "unknown")
    preferred_shell = f"{preferred} (PowerShell 7 if available)"

    sep_char = "\\"
    codepage = env.get("encoding", {}).get("cmd_codepage", "unknown")
    long_paths = env.get("long_path_support")
    long_paths_str = "yes" if long_paths else "no/unknown"

    tools = env.get("path_tools", {})
    available = [name for name, path in tools.items() if path]
    tools_str = ", ".join(available) if available else "none detected"

    template = _load_template()
    return template.format(
        os=os_str,
        preferred_shell=preferred_shell,
        sep_char=sep_char,
        codepage=codepage,
        long_paths=long_paths_str,
        tools=tools_str,
    )


def main() -> int:
    env = EnvDetect().detect()
    print(generate_prompt(env))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
