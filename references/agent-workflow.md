# Agent Workflow Examples

This file shows how an agent should use the `windows-runtime` skill on Windows. It is reference material — read it when you need concrete command patterns, not on every invocation.

## Scenario 1: Session start — environment awareness

Before running commands, detect the environment to decide shell strategy:

```powershell
python scripts/cli.py detect --json
```

Sample output (truncated):
```json
{
  "os": {"system": "Windows", "release": "10", "machine": "AMD64"},
  "shell": {
    "preferred": "powershell",
    "available": {"pwsh": {"available": false}, "powershell": {"available": true}, "cmd": {"available": true}, "bash": {"available": false}}
  },
  "encoding": {"cmd_codepage": "936"},
  "path_tools": {"python": "C:\\...\\python.exe", "git": "C:\\...\\git.exe"}
}
```

**Decision:** preferred shell is `powershell` (falls back to PS5 since no pwsh); codepage 936 means UTF-8 is forced at execution time.

## Scenario 2: Before generating commands — translation check

Verify Bash-style commands translate correctly before executing:

```powershell
python scripts/cli.py translate "rm -rf ./build"
# → Remove-Item -Path './build' -Recurse -Force -ErrorAction SilentlyContinue | Out-Null

python scripts/cli.py translate "mkdir -p ./build/output"
# → if (-not (Test-Path './build/output')) { New-Item -ItemType Directory -Path './build/output' -Force | Out-Null }

python scripts/cli.py translate "cat app.log | grep ERROR"
# → Select-String -Path 'app.log' -Pattern 'ERROR' -CaseSensitive:$false
```

If you omit `--shell`, the detected preferred shell is used automatically.

## Scenario 3: Direct execution — translate + run

To inspect an env var or list a directory, use `exec` (auto-translate + UTF-8 execute + standard JSON):

```powershell
python scripts/cli.py exec "echo $PATH" --json
```

```json
{
  "ok": true,
  "stdout": "C:\\Python311\\Scripts;...",
  "stderr": "",
  "exit_code": 0,
  "shell_used": "powershell",
  "translated_cmd": "Write-Output $env:PATH",
  "matched_rule": "echo env",
  "fallback": false
}
```

Chinese paths render correctly (UTF-8 decode):
```powershell
python scripts/cli.py exec "ls ./项目文档" --json
```

## Scenario 4: Fragile operations — use wrap to bypass the shell

For delete / create / read / write / search, prefer `wrap` (Python-native via `pathlib`/`shutil`) over shell commands:

```powershell
python scripts/cli.py wrap rm ./old_cache
python scripts/cli.py wrap mkdir ./dist/assets
python scripts/cli.py wrap write ./config/settings.json "{\"key\": \"value\"}"
python scripts/cli.py wrap grep "TODO" "src/*.py"
python scripts/cli.py wrap find ./src "*.md"
```

## Scenario 5: Inject environment context into a downstream agent

When dispatching a sub-task to another agent (or building a system prompt for Codex CLI / OpenCode / Hermes), generate an environment fragment:

```powershell
python scripts/cli.py prompt
```

Output can be pasted directly into the sub-agent's system prompt (see assets/prompt-template.txt for the template).

## Decision tree (agent built-in logic)

```
Receive a shell command request
  │
  ├─ Is it a fragile op (delete / mkdir / read / write / grep / find)?
  │     └─ Yes → use wrap subcommand (rm / mkdir / write / read / grep / find)
  │
  └─ No → needs execution?
        ├─ Yes → exec subcommand (auto-translate + UTF-8 + JSON)
        └─ No → only need syntax? → translate subcommand
```

Run `detect` + `prompt` once at session start; afterwards follow the tree with `wrap` / `exec` / `translate`.
