# Tool Wrappers

This skill provides Python-based safe wrappers for common file and shell operations. Use them instead of generating raw shell commands when possible, especially on Windows where shell differences are large.

## Operations

| Function | Usage | Notes |
|----------|-------|-------|
| `safe_rm(path)` | Remove file or directory recursively | Uses `shutil.rmtree(..., ignore_errors=True)` |
| `safe_mkdir(path)` | Create directory recursively | Returns `Path` object |
| `safe_copy(src, dst)` | Copy file or directory recursively | Uses `shutil.copy2` / `shutil.copytree` |
| `safe_move(src, dst)` | Move file or directory | |
| `safe_read(path)` | Read text file | Tries UTF-8, then GBK, then cp1252 |
| `safe_write(path, content)` | Write text file | Creates parent directories |
| `safe_grep(pattern, files)` | Search regex across files | Returns `file:line:match` strings |
| `safe_find(root, pattern)` | Find files matching glob | Uses `pathlib.Path.rglob` |
| `safe_env(name, value=None)` | Get or set environment variable | |
| `safe_path(path)` | Normalize and return absolute path | |

## CLI usage

```powershell
python scripts/tool_wrap.py rm ./temp
python scripts/tool_wrap.py mkdir ./build/output
python scripts/tool_wrap.py read ./file.txt
python scripts/tool_wrap.py grep "class.*Agent" ./scripts/*.py
python scripts/tool_wrap.py find . "*.py"
```

## Why use wrappers

- Avoid shell quoting and escaping errors.
- Avoid path separator mismatches (`/` vs `\\`).
- Avoid encoding issues when reading/writing files.
- Avoid permissions/file-lock problems with Python's `ignore_errors` options.
