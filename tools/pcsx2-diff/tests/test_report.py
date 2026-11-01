import json

from l3.compare import Divergence
from l3.report import append_history, make_record, write_report


def test_report_lists_divergent_fields(tmp_path):
    d = Divergence(812, {"rider0_pos": ([1.0, 2.0, 3.0], [1.0, 2.5, 3.0]), "score": ([5], [6])})
    p = tmp_path / "report.md"
    write_report(p, "p1_race_snow_jam", "abc1234", d, meta={"native_race_start": 3552})
    text = p.read_text()
    assert "812" in text and "rider0_pos" in text and "score" in text
    assert "| score | 5 | 6 |" in text
    assert "3552" in text


def test_report_without_divergence(tmp_path):
    p = tmp_path / "report.md"
    write_report(p, "s", "abc1234", None, meta={})
    assert "No divergence" in p.read_text()


def test_history_appends_one_line(tmp_path):
    h = tmp_path / "history.jsonl"
    append_history(h, make_record("abc1234", "s", "per-frame", Divergence(7, {"a": ([1], [2])})))
    append_history(h, make_record("def5678", "s", "per-frame", None))
    rows = [json.loads(l) for l in h.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0] == {"commit": "abc1234", "scenario": "s", "mode": "per-frame",
                       "first_divergence_frame": 7, "fields": ["a"]}


def test_no_divergence_writes_null():
    r = make_record("abc1234", "s", "per-frame", None)
    assert r["first_divergence_frame"] is None and r["fields"] == []
