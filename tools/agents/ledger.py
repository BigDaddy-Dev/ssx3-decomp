#!/usr/bin/env python3
"""Cost ledger for the writer agents (one JSON line per model call).

  python3 tools/agents/ledger.py status                    # spend, pass rates, cost per function
  python3 tools/agents/ledger.py mark FN ATTEMPT pass|fail # the orchestrator's test result

Only OpenRouter spend counts toward the monthly cap (SSX3_AGENT_BUDGET_USD, default 50);
Claude escalations are logged with provider "claude" and run on the user's Claude plan.
An OpenRouter call whose cost is unknown blocks new writers until a person reviews it.
"""
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "ledger.jsonl"


@dataclass
class Entry:
    ts: str
    fn: str
    wave: str
    provider: str  # "openrouter" | "claude"
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float | None
    attempt: int
    result: str  # "pass" | "fail" | "error" | "skipped"


def append(path, entry):
    with open(path, "a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")


def read(path):
    p = Path(path)
    if not p.exists():
        return []
    return [Entry(**json.loads(line)) for line in p.read_text().splitlines() if line.strip()]


def mark(path, fn, attempt, result):
    """Record the orchestrator's test result on the latest pending entry for fn/attempt."""
    rows = read(path)
    for x in reversed(rows):
        if x.fn == fn and x.attempt == attempt and x.result == "pending":
            x.result = result
            Path(path).write_text("".join(json.dumps(asdict(r)) + "\n" for r in rows))
            return True
    return False


def _this_month(entries, now):
    for x in entries:
        t = datetime.fromisoformat(x.ts).astimezone(timezone.utc)
        if (t.year, t.month) == (now.year, now.month):
            yield x


def month_spend(entries, now):
    return round(sum(x.cost_usd or 0.0 for x in _this_month(entries, now) if x.provider == "openrouter"), 6)


def budget_ok(entries, now, cap):
    unknown = [x.fn for x in _this_month(entries, now) if x.provider == "openrouter" and x.cost_usd is None]
    if unknown:
        return False, f"cost unknown for {', '.join(unknown)}: review the ledger before starting more writers"
    spent = month_spend(entries, now)
    if spent >= cap:
        return False, f"monthly OpenRouter budget reached: ${spent:.2f} of ${cap:.2f}"
    return True, f"${spent:.2f} of ${cap:.2f} spent this month"


def status(entries, now):
    rows = list(_this_month(entries, now))
    lines = [f"OpenRouter spend {now:%Y-%m}: ${month_spend(entries, now):.2f}"]
    by_model = defaultdict(list)
    for x in rows:
        by_model[x.model].append(x)
    for model, xs in sorted(by_model.items()):
        passed = sum(x.result == "pass" for x in xs)
        cost = sum(x.cost_usd or 0.0 for x in xs)
        per_fn = f"${cost / passed:.2f}" if passed else "n/a"
        lines.append(f"  {model}: {passed}/{len(xs)} pass ({100 * passed // len(xs)}%), "
                     f"${cost:.2f}, {per_fn} per passed function")
    return "\n".join(lines)


def main(argv):
    path = os.environ.get("SSX3_AGENT_LEDGER", DEFAULT_PATH)
    if argv[:1] == ["mark"] and len(argv) == 4 and argv[3] in ("pass", "fail"):
        if not mark(path, argv[1], int(argv[2]), argv[3]):
            sys.exit(f"ledger: no pending entry for {argv[1]} attempt {argv[2]}")
        return
    if argv[:1] != ["status"]:
        sys.exit(__doc__)
    print(status(read(path), datetime.now(timezone.utc)))
    cap = float(os.environ.get("SSX3_AGENT_BUDGET_USD", "50"))
    print(budget_ok(read(path), datetime.now(timezone.utc), cap)[1])


if __name__ == "__main__":
    main(sys.argv[1:])
