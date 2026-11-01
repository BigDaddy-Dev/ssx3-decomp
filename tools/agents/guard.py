"""Reject a writer's work unless it changed exactly its one module file (AGENTS.md, writer rules)."""


def check_diff(name_status, allowed):
    """name_status: (status, path) pairs from `git diff --name-status`. Returns violations ([] = ok)."""
    if not name_status:
        return ["the writer produced no change to its module file"]
    out = []
    for status, path in name_status:
        if path != allowed:
            out.append(f"{path}: writers may only edit {allowed}")
        elif status not in ("M", "A"):
            out.append(f"{path}: status {status} not allowed (only modify or add)")
    return out
