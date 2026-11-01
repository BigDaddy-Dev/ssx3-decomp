import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ledger  # noqa: E402
from ledger import Entry  # noqa: E402

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def e(cost, provider="openrouter", ts="2026-11-02T10:00:00+00:00", model="openrouter/qwen/qwen3-coder",
      result="pass", fn="f_00100000", attempt=1):
    return Entry(ts=ts, fn=fn, wave="w1", provider=provider, model=model, tokens_in=100,
                 tokens_out=50, cost_usd=cost, attempt=attempt, result=result)


def test_budget_blocks_at_cap():
    assert ledger.budget_ok([e(50.00)], NOW, 50.0)[0] is False
    assert ledger.budget_ok([e(49.99)], NOW, 50.0)[0] is True


def test_budget_resets_new_month():
    old = e(50.00, ts="2026-10-31T23:59:59+00:00")
    assert ledger.month_spend([old], NOW) == 0.0
    assert ledger.budget_ok([old], NOW, 50.0)[0] is True


def test_claude_not_counted():
    assert ledger.month_spend([e(30.0, provider="claude"), e(1.5)], NOW) == 1.5


def test_unknown_cost_blocks():
    ok, msg = ledger.budget_ok([e(None, fn="f_003de768")], NOW, 50.0)
    assert ok is False
    assert "f_003de768" in msg


def test_unknown_claude_cost_does_not_block():
    assert ledger.budget_ok([e(None, provider="claude")], NOW, 50.0)[0] is True


def test_append_and_read_roundtrip(tmp_path):
    p = tmp_path / "ledger.jsonl"
    ledger.append(p, e(0.25))
    ledger.append(p, e(None, result="error"))
    got = ledger.read(p)
    assert [x.cost_usd for x in got] == [0.25, None]


def test_read_missing_file_is_empty(tmp_path):
    assert ledger.read(tmp_path / "nope.jsonl") == []


def test_status_pass_rate_per_model():
    rows = [e(0.1), e(0.1, result="fail"), e(0.1, model="openrouter/deepseek/deepseek-chat")]
    out = ledger.status(rows, NOW)
    assert "openrouter/qwen/qwen3-coder" in out and "50%" in out
    assert "openrouter/deepseek/deepseek-chat" in out and "100%" in out
    assert "$0.30" in out
