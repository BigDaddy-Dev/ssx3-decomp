#!/usr/bin/env python3
"""Pre-commit guard: refuse to commit game material (docs/local/state.md, spec in retro-vault).

A superset of .github/workflows/no-game-material.yml: the disc, extracted or
generated code, RAM/VRAM/GS dumps, savestates, and binaries over 1 MiB.
"""
import re
import subprocess
import sys

MAX_BINARY = 1_048_576
BLOCKED = re.compile(
    r"\.iso$|^orig/|^generated/|SLUS_207\.72|(^|/)(ram|vram)[^/]*\.bin$|\.(gs|p2s)$",
    re.IGNORECASE,
)


def check(entries):
    """entries: (status, path, size_bytes, is_binary). Returns one message per violation."""
    out = []
    for status, path, size, is_binary in entries:
        if status.startswith("D"):
            continue
        if BLOCKED.search(path):
            out.append(f"{path}: game material (orig/, generated/, disc, dumps) must never be committed")
        elif is_binary and size > MAX_BINARY:
            out.append(f"{path}: binary of {size} bytes is over the 1 MiB limit")
    return out


def _staged():
    raw = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z", "--find-renames"],
        check=True, capture_output=True,
    ).stdout.decode()
    parts = raw.split("\0")
    i = 0
    while i < len(parts) - 1:
        status = parts[i]
        # Renames and copies carry two paths; the new path is the one that lands.
        path = parts[i + 2] if status[:1] in "RC" else parts[i + 1]
        i += 3 if status[:1] in "RC" else 2
        if status.startswith("D"):
            yield status, path, 0, False
            continue
        blob = subprocess.run(["git", "show", f":{path}"], check=True, capture_output=True).stdout
        yield status, path, len(blob), b"\0" in blob[:8192]


def main():
    problems = check(list(_staged()))
    for p in problems:
        print(f"pre-commit: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
