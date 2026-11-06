#!/usr/bin/env python3
"""
generate_tree.py - Lightweight repository file tree generator for documentation.
Outputs an ASCII or Markdown tree while skipping VCS, virtual environments,
caches, and build artifacts.
"""

import sys
from pathlib import Path

DEFAULT_IGNORES = {
    ".git", ".svn", ".hg",
    "node_modules", "bower_components",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", ".env",
    "dist", "build", "out", "target", ".next", ".nuxt",
    ".idea", ".vscode", ".DS_Store", "*.pyc"
}

def is_ignored(name: str, ignores: set) -> bool:
    if name in ignores:
        return True
    for pat in ignores:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
    return False

def build_tree(root_dir: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> list:
    if current_depth > max_depth:
        return []

    lines = []
    try:
        entries = sorted(list(root_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return [f"{prefix}[Permission Denied]"]

    entries = [e for e in entries if not is_ignored(e.name, DEFAULT_IGNORES)]
    total = len(entries)

    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            lines.extend(build_tree(entry, prefix + child_prefix, max_depth, current_depth + 1))
        else:
            lines.append(f"{prefix}{connector}{entry.name}")

    return lines

def main():
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: {target_path} is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"{target_path.resolve().name}/")
    tree_lines = build_tree(target_path, max_depth=max_depth)
    for line in tree_lines:
        print(line)

if __name__ == "__main__":
    main()
