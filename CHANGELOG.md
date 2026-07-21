# Changelog

All notable changes to this skill are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Error Recovery Engine** (`scripts/recovery.py`) — deterministic,
  no-LLM recovery layer. Classifies a failed `exec` result into one of 10
  categories (`command_not_found`, `permission_denied`, `path_not_found`,
  `syntax_error`, `encoding_mojibake`, `file_in_use`, `python_not_found`,
  `git_not_available`, `timeout_or_hung`, `admin_required`), emits
  human-readable `fix_hint`s, and — where safe — a self-contained
  `auto_recovery` action the runner can retry once.
  - Auto-recovery builders: `where.exe` full-path re-resolution for missing
    commands, `cmd`+GBK re-decode for mojibake output, `python3` fallback.
  - Never guesses: if `where.exe` cannot resolve the tool, no action is
    produced (the failure surfaces honestly).
- **Retry / recovery closed loop** in `ExecRunner.run()` — Stage 1 naive
  OS/timeout retries, Stage 2 deterministic recovery. `--recover` is on by
  default; `exec --no-recover` disables it. Recovery metadata is attached to
  the result (`recovery`, `recovered_via`).
- **Path Resolver** (`scripts/path_resolver.py` + `resolve` subcommand) —
  normalizes `~`, `.`/`..`, `//UNC`, `\\server\share`, `/mnt/c/...` (WSL),
  `C:/x//y` (mixed/duplicate separators), and `\\?\` long-path passthrough
  into a canonical absolute Windows path.
- **Tool Discovery** (`scripts/tool_discovery.py` + `discover` subcommand) —
  resolves a logical tool name (`git`/`python`/`node`/...) to the best
  concrete executable, preferring real `.exe` over `.cmd`/`.bat`/`.ps1`
  wrappers and excluding QClaw's `bash.cmd` false positive.
- `recover` subcommand — analyze an `exec` result JSON and print recovery
  suggestions without executing anything.
- `capabilities` subcommand — emits a declarative Capabilities Manifest for
  agent *planning*: which ops to route through `wrap` (native, no shell) vs
  `exec` (needs a shell), plus detected toolchain versions and platform facts.
- `env_detect` capability extension: detected versions for `python`, `node`,
  `npm`, `git`, `cargo`, `go`, `java`, `docker`; plus `wsl` (real distro
  installed?), `admin` (elevation), `network` (outbound probe).
- `scripts/capabilities.py` — manifest builder (`build_manifest`) consumed by
  both `capabilities` and `detect`.
- SKILL.md section + Quick start entry for the `capabilities` manifest.

### Fixed
- `command_not_found` pattern now also matches PowerShell's wording
  ("is not recognized as a name of a cmdlet"), not only cmd.exe's phrasing.
- Path Resolver `re.sub` replacement escaping — duplicate/mixed separators
  (`C:/x//y`, `relative/dir`) previously raised `bad escape`; fixed.

## [1.0.0] - 2026-07-21

### Added
- Initial release of the Windows Agent Compatibility layer.
- `detect` — environment, shell availability (pwsh/powershell/cmd/bash), code
  page, and path-tool probing. `--json` for machine use.
- `translate` — Bash-style command → pwsh/cmd/bash syntax. Auto-selects the
  best available shell when `--shell` is omitted.
- `exec` — translate + execute with encoding handling; returns a standard JSON
  result (`ok`, `stdout`, `stderr`, `exit_code`, `shell_used`,
  `translated_cmd`, `matched_rule`, `fallback`).
- `wrap` — shell-independent safe file wrappers: `rm`, `mkdir`, `copy`, `move`,
  `read`, `write`, `grep`, `find`, `env`, `path`.
  - `write` supports `--from-file <src>` so multi-line content survives shell
    quoting (CLI args cannot carry newlines reliably).
- `prompt` — renders an environment fragment (shell, encoding, path separator,
  available tools, bash intentionally omitted when only a WSL stub exists) to
  inject into a sub-agent's system prompt.
- Per-shell command registry and shell matrix references.
- ANSI color stripping via `$PSStyle.OutputRendering = 'PlainText'` in `exec`
  so PowerShell table/`Select-String` output stays machine-parseable.
- Encoding fallback chain `utf-8 → gbk → cp1252 → utf-16` (UTF-16 last-resort)
  to avoid GBK mojibake on Chinese Windows.
- 71-assertion regression harness covering 8 scenarios (detect / translate /
  exec / prompt / wrap / output_parser / edge / structure).

### Fixed
- cmd templates used single quotes (invalid in `cmd.exe`) → switched to double
  quotes; verified by real execution.
- `Select-String` emitted ANSI highlight codes → added
  `| ForEach-Object { $_.Line }` to strip coloring.
- `safe_grep` iterated a `./glob` string character-by-character (caused
  `PermissionDenied` on `.`) → normalize to list, use `glob.glob(root_dir=cwd)`.
- UTF-16 decode was attempted before GBK → swapped order so GBK wins on
  Chinese Windows.
- `exec` produced ANSI-colored stdout on PowerShell → disabled `OutputRendering`.
- `wrap write` could not receive multi-line content via CLI args → added
  `--from-file`.

### Discovered via real task simulation (not unit tests)
- `wrap write` multi-line argument loss (all shells) → `--from-file` fix.
- `exec ls` ANSI pollution → `OutputRendering='PlainText'` fix.

[1.0.0]: https://github.com/ZJXMGMV/windows-agent-compat/releases/tag/v1.0.0
