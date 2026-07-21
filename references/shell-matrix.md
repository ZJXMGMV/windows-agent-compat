# Shell Comparison Matrix

| Feature | PowerShell 7 | Windows PowerShell 5 | cmd.exe | Git Bash |
|---------|--------------|----------------------|---------|----------|
| Command separator | `;` | `;` | `&&`, `\|\|` | `;` |
| Environment variable | `$env:NAME` | `$env:NAME` | `%NAME%` | `$NAME` |
| Set env var | `$env:NAME = value` | `$env:NAME = value` | `set NAME=value` | `export NAME=value` |
| Remove directory | `Remove-Item -Recurse -Force` | `Remove-Item -Recurse -Force` | `rmdir /S /Q` | `rm -rf` |
| Copy recursive | `Copy-Item -Recurse` | `Copy-Item -Recurse` | `xcopy /E /I /Y` | `cp -r` |
| Search in files | `Select-String` | `Select-String` | `findstr` | `grep` |
| List directory | `Get-ChildItem` | `Get-ChildItem` | `dir` | `ls` |
| Print working dir | `Get-Location` | `Get-Location` | `cd` | `pwd` |
| Find command path | `Get-Command` | `Get-Command` | `where` | `which` |
| Head (first N lines) | `Get-Content -TotalCount N` | `Get-Content -TotalCount N` | `more +0 \| findstr /N` | `head -n N` |
| Tail (last N lines) | `Get-Content -Tail N` | `Get-Content -Tail N` | `powershell -Command ...` | `tail -n N` |
| Count lines | `Measure-Object -Line` | `Measure-Object -Line` | `find /C /V ""` | `wc -l` |
| Quote executable | `& "path with spaces"` | `& "path with spaces"` | `"path with spaces"` | `"path with spaces"` |
| Path separator | `/` or `\` | `/` or `\` | `\` | `/` or `\` |
| Exit code semantics | `exit $LASTEXITCODE` | `exit` | `exit /b` | `exit` |
| Output type | Objects + strings | Objects + strings | Strings | Strings |
| Suppress errors | `-ErrorAction SilentlyContinue` | `-ErrorAction SilentlyContinue` | `2>nul` | `2>/dev/null` |
| Null redirect | `\| Out-Null` | `\| Out-Null` | `>nul 2>&1` | `>/dev/null 2>&1` |
