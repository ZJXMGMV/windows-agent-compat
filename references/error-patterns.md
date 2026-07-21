# Common Error Patterns

Common errors when agents run Linux/Bash-style commands on Windows and how this skill handles them.

## 1. Permission denied / 访问被拒绝

**Cause:** Windows locks files that are open in VS Code, Chrome, Explorer, etc.

**Handling:**
- `ExecRunner` retries the command up to the configured retry count.
- `safe_rm` uses Python `shutil.rmtree(..., ignore_errors=True)` which is more tolerant than `rm -rf`.

## 2. Command not found / 不是内部或外部命令

**Cause:** Agent generated a Bash command on native Windows.

**Handling:**
- `CommandTranslator` maps known Bash commands to PowerShell/cmd equivalents.
- Unknown commands fall back to path/quote normalization.

## 3. 找不到路径 / 找不到文件

**Cause:** Forward slashes, missing drive letters, or WSL paths (`/mnt/c/...`).

**Handling:**
- Path normalization converts `/` to `\\` for cmd and preserves valid separators for pwsh.
- Tool wrappers use `pathlib.Path` to resolve absolute paths.

## 4. 命令语法不正确

**Cause:** Agent mixed shell syntax (e.g., `set` in PowerShell or `export` in cmd).

**Handling:**
- Translate `export` to `$env:` in PowerShell and `set` in cmd.
- Translate `echo $PATH` to `Write-Output $env:PATH` in PowerShell.

## 5. PowerShell exit code 0 but stderr warnings

**Cause:** PowerShell writes non-fatal warnings to stderr.

**Handling:**
- `OutputParser` treats exit code 0 as OK unless stderr contains fatal keywords (`error`, `exception`, `terminated`, `失败`).

## 6. PowerShell object output instead of string

**Cause:** `Get-Content` returns an array of objects.

**Handling:**
- `OutputParser._stringify` joins arrays into strings.
- `ExecRunner` runs with `-Command` and explicitly returns strings where possible.

## 7. chmod +x has no effect

**Cause:** Windows has no executable bit.

**Handling:**
- `chmod +x` is translated to a no-op comment in PowerShell/cmd.
- Use `safe_rm` / `safe_mkdir` instead of shell commands for file operations.

## 8. Long path errors (>260 chars)

**Cause:** Classic Windows path length limit.

**Handling:**
- `safe_*` wrappers use `pathlib` which supports long paths when the system enables it.
- `EnvDetect` reports `LongPathsEnabled` registry value.

## 9. UTF-8 / GBK encoding issues

**Cause:** cmd/PowerShell/Python may use different encodings.

**Handling:**
- `ExecRunner` captures raw bytes and decodes with fallback chain: UTF-8 → GBK → cp1252.
- `safe_read` / `safe_write` default to UTF-8 with fallback on read.
