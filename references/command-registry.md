# Command Registry

This file documents the Bash-to-Windows command translation rules implemented in `config/adapters.json`.

## File Operations

| Bash Pattern | PowerShell | cmd | Git Bash |
|-------------|--------------|-----|----------|
| `rm -rf <path>` | `Remove-Item -Path '<path>' -Recurse -Force -ErrorAction SilentlyContinue \| Out-Null` | `rmdir /S /Q '<path>' 2>nul \|\| del /F /Q '<path>' 2>nul` | `rm -rf '<path>'` |
| `rm -f <path>` | `Remove-Item -Path '<path>' -Force -ErrorAction SilentlyContinue` | `del /F /Q '<path>' 2>nul` | `rm -f '<path>'` |
| `mkdir -p <path>` | `if (-not (Test-Path '<path>')) { New-Item -ItemType Directory -Path '<path>' -Force \| Out-Null }` | `if not exist '<path>' mkdir '<path>' >nul 2>&1` | `mkdir -p '<path>'` |
| `cp -r <src> <dst>` | `Copy-Item -Path '<src>' -Destination '<dst>' -Recurse -Force` | `xcopy '<src>' '<dst>' /E /I /Y` | `cp -r '<src>' '<dst>'` |
| `mv <src> <dst>` | `Move-Item -Path '<src>' -Destination '<dst>' -Force` | `move /Y '<src>' '<dst>'` | `mv '<src>' '<dst>'` |
| `touch <path>` | `if (Test-Path '<path>') { (Get-Item '<path>').LastWriteTime = Get-Date } else { New-Item -ItemType File -Path '<path>' -Force \| Out-Null }` | `copy /Y nul '<path>' >nul 2>&1` | `touch '<path>'` |

## Content Operations

| Bash Pattern | PowerShell | cmd | Git Bash |
|-------------|--------------|-----|----------|
| `cat <file>` | `Get-Content -Path '<file>' -Raw` | `type '<file>'` | `cat '<file>'` |
| `cat <file> \| grep <pattern>` | `Select-String -Path '<file>' -Pattern '<pattern>' -CaseSensitive:$false` | `findstr /I /C:"<pattern>" "<file>"` | `cat '<file>' \| grep '<pattern>'` |
| `grep <flags> <pattern> <file>` | `Select-String -Path '<file>' -Pattern '<pattern>' -CaseSensitive:$false` | `findstr /I /C:"<pattern>" "<file>"` | `grep <flags> '<pattern>' '<file>'` |
| `head -n <n> <file>` | `Get-Content -Path '<file>' -TotalCount <n>` | `more +0 "<file>" \| findstr /N . \| findstr /B "^[1-<n>]:"` | `head -n <n> '<file>'` |
| `tail -n <n> <file>` | `Get-Content -Path '<file>' -Tail <n>` | `powershell -NoProfile -Command "Get-Content -Path '<file>' -Tail <n>"` | `tail -n <n> '<file>'` |
| `wc -l <file>` | `(Get-Content -Path '<file>' \| Measure-Object -Line).Lines` | `find /C /V "" < "<file>"` | `wc -l '<file>'` |

## Search Operations

| Bash Pattern | PowerShell | cmd | Git Bash |
|-------------|--------------|-----|----------|
| `find <root> -name <pattern>` | `Get-ChildItem -Path '<root>' -Recurse -Filter '<pattern>' -ErrorAction SilentlyContinue \| Select-Object -ExpandProperty FullName` | `dir /S /B "<root>\<pattern>"` | `find '<root>' -name '<pattern>'` |

## Listing Operations

| Bash Pattern | PowerShell | cmd | Git Bash |
|-------------|--------------|-----|----------|
| `ls <flags> <path>` | `Get-ChildItem -Path '<path>' -Force` | `dir <path>` | `ls <flags> '<path>'` |
| `ls <path>` | `Get-ChildItem -Path '<path>'` | `dir <path>` | `ls '<path>'` |
| `ls` (bare) | `Get-ChildItem` | `dir` | `ls` |
| `pwd` | `Get-Location \| Select-Object -ExpandProperty Path` | `cd` | `pwd` |
| `which <cmd>` | `Get-Command <cmd> -ErrorAction SilentlyContinue \| Select-Object -ExpandProperty Source` | `where <cmd>` | `which <cmd>` |

## Environment Operations

| Bash Pattern | PowerShell | cmd | Git Bash |
|-------------|--------------|-----|----------|
| `export NAME=value` | `$env:NAME = 'value'` | `set NAME=value` | `export NAME=value` |
| `unset NAME` | `Remove-Item -Path env:NAME -ErrorAction SilentlyContinue` | `set NAME=` | `unset NAME` |
| `echo $NAME` | `Write-Output $env:NAME` | `echo %NAME%` | `echo $NAME` |
| `echo <text>` | `Write-Output "<text>"` | `echo <text>` | `echo <text>` |

## Special Operations

| Bash Pattern | PowerShell | cmd | Git Bash |
|-------------|--------------|-----|----------|
| `chmod +x <path>` | `# chmod has no equivalent on Windows; skipped` | `REM chmod has no equivalent on Windows` | `chmod +x '<path>'` |

## Shell Aliases

The translator recognizes both `pwsh` and `powershell` as shell names. `powershell` is internally aliased to `pwsh` so the same template is used for both.

## Rule Ordering

Rules are matched in the order they appear in `adapters.json`. More specific patterns (e.g. `cat | grep`) must come before more general ones (e.g. `cat`). The `echo env` rule must come before `echo literal` to prevent `echo $PATH` from being matched as a literal echo.

## Empty Capture Handling

When a capture group matches an empty string (e.g. `ls -la` with no path), the `_render` method in `cmd_adapter.py` automatically strips empty `-Path ''` parameters and cleans up double spaces.

## Adding new rules

Edit `config/adapters.json` and add a new entry under `commands`. The `pattern` field is a Python regex. Use named capture groups and reference them with `{{name}}` in the shell templates.
