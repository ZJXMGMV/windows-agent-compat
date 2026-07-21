# windows-agent-compat

A Windows command compatibility layer for AI agents. It lets an agent that was
trained on Bash/Linux idioms operate correctly on Windows by **translating
Bash-style commands to the best available Windows shell** (PowerShell 7 →
Windows PowerShell 5 → cmd → Git Bash) and by providing **safe, cross-shell
file-operation wrappers**.

Targets: **OpenClaw**, **Codex CLI**, **OpenCode**, **Hermes**, and any other
agent framework that shells out to a Windows command line.

---

## Why this exists

When an agent trained on Linux issues commands like `rm -rf`, `mkdir -p`,
`cat f | grep x`, `ls -la`, `chmod +x`, `find . -name '*.py'` on Windows, it
hits a wall of silent failures:

- `rm`/`mkdir -p`/`cat`/`ls` don't exist in `cmd.exe`
- single quotes are invalid in `cmd.exe`
- PowerShell uses `Remove-Item`/`New-Item`/`Get-Content`/`Get-ChildItem`
- Chinese Windows outputs GBK, not UTF-8 → mojibake
- `Get-ChildItem` / `Select-String` emit ANSI color codes that pollute
  machine-parsed output
- multi-line file content can't be passed safely through CLI arguments
- `bash` on Windows may be a WSL stub without a distro installed

This skill handles all of the above so the agent doesn't have to.

---

## Install

```powershell
git clone https://github.com/ZJXMGMV/windows-agent-compat.git
# Drop the skill folder into your agent's skills directory, e.g.:
#   OpenClaw:  ~/.qclaw/skills/windows-agent-compat/
#   Codex:     .codex/skills/windows-agent-compat/  (see your framework docs)
```

The skill is pure Python 3 (standard library only). No third-party deps.

---

## Quick start

```powershell
$CLI = "C:\Users\Administrator\.qclaw\skills\windows-agent-compat\scripts\cli.py"

python $CLI detect --json          # what shells/tools/encoding are available?
python $CLI translate "rm -rf x"   # Bash -> PowerShell (auto shell)
python $CLI translate "rm -rf x" --shell cmd
python $CLI exec "ls ." --json     # translate + run, returns structured JSON
python $CLI wrap mkdir ./out       # safe op (no shell quoting hazards)
python $CLI wrap write ./f.md --from-file ./content.txt
python $CLI prompt                 # env fragment to inject into a sub-agent
```

---

## Subcommands

| Command | Purpose |
|---------|---------|
| `detect` | Probe the environment: OS, preferred shell, available shells (`pwsh`/`powershell`/`cmd`/`bash`), code page, path tools. `--json` for machine use. |
| `translate` | Convert a Bash-style command into the target shell's syntax. `--shell pwsh\|powershell\|cmd\|bash` (default: auto). |
| `exec` | Translate and execute a command, returning a standard JSON result (`ok`, `stdout`, `stderr`, `exit_code`, `shell_used`, `translated_cmd`, `matched_rule`, `fallback`). `--json` required for structured output. |
| `wrap` | Run a **safe, shell-independent** file operation. Use this for fragile ops instead of hand-built shell strings. |
| `prompt` | Render an environment-description fragment (shell, encoding, path separator, available tools) to inject into a sub-agent's system prompt. `--json` for structured use. |

### `wrap` operations

```
rm <path>            remove file or directory (recursive)
mkdir <path>         create dir + parents
copy <src> <dst>     copy file or directory
move <src> <dst>     move file or directory
read <path>          read text (utf-8 -> gbk -> cp1252 fallback)
write <path> <text>  write text; multi-line via --from-file <src>
grep <pat> <files>   grep across globs/paths (case-insensitive)
find <root> <glob>   recursive file find
env <NAME>           read env var
path <p>             normalized absolute path
```

---

## Supported command translations

`rm -rf`, `rm -f`, `mkdir -p`, `cp -r`, `mv`, `touch`, `cat`, `export`,
`unset`, `echo $VAR`, `echo literal`, `chmod +x` (best-effort note), `ls`,
`pwd`, `which`, `head`, `tail`, `wc -l`, `find -name`, `cat | grep`,
`grep -i`.

See [`references/command-registry.md`](references/command-registry.md) for the
full list and [`references/shell-matrix.md`](references/shell-matrix.md) for
the per-shell mapping.

---

## Shell compatibility matrix

| Shell | Auto rank | Notes |
|-------|-----------|-------|
| `pwsh` (PowerShell 7+) | 1 | Preferred. Cleanest UTF-8 + JSON output. |
| `powershell` (5.1) | 2 | Always present on Windows; fallback when pwsh absent. |
| `cmd` | 3 | No native `tail`/`grep`/`chmod`; delegates or best-effort. |
| `bash` | 4 | May be a WSL stub with no distro → fails with a clear message. |

---

## Design notes

- **Encoding:** PowerShell output is forced to UTF-8; stdout/stderr are decoded
  `utf-8 → gbk → cp1252 → utf-16` (UTF-16 is last-resort only, because it can
  silently "decode" GBK bytes into mojibake).
- **ANSI stripping:** `exec` sets `$PSStyle.OutputRendering = 'PlainText'` so
  `Get-ChildItem` / `Select-String` never pollute parsed output with color codes.
- **Multi-line content:** pass file content with `wrap write <path> --from-file
  <src>` — never through a CLI argument (shell quoting mangles newlines).
- **`grep` safety:** globs are expanded with `root_dir=os.getcwd()` to avoid
  `scandir('.')` permission errors on Windows.

---

## Development & testing

```powershell
# Syntax check all scripts
python -m py_compile scripts/*.py

# The skill ships with a regression harness (run from workspace):
python _full_regression.py   # 71 assertions across 8 scenarios
```

---

## License

MIT.
