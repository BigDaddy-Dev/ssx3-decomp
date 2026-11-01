import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dispatch  # noqa: E402
import ledger  # noqa: E402

FIXTURE = HERE / "fixtures" / "opencode-run.jsonl"
FAKE = HERE / "fixtures" / "fake_opencode.py"
MOD = "crates/ssx3-game/src/oc7.rs"
FN = "f_00100000"
AGENTS_MD = """# Goals
## Porting loop
### Subagent (writer)

- **One function, then stop.** Port only the single function you were given.
- Never run cargo.

---

## Tick-rate pass
"""


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    (r / "crates/ssx3-game/src").mkdir(parents=True)
    (r / "docs/investigation").mkdir(parents=True)
    (r / "AGENTS.md").write_text(AGENTS_MD)
    (r / "overrides.txt").write_text("")
    (r / "docs/investigation/phase2-worker-guide.md").write_text("guide\n")
    (r / ".gitignore").write_text("/generated/\n")
    (r / "generated").mkdir()
    (r / "generated" / "ee.rs").write_text("// generated\n")
    git(r, "init", "-q")
    git(r, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git(r, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    # Staging module and dossier are uncommitted, as in a real wave.
    (r / MOD).write_text("// oc7 staging\n")
    (r / "ref1").mkdir()
    (r / "ref1" / f"{FN}.md").write_text("dossier\n")
    monkeypatch.setenv("OPENCODE_BIN", str(FAKE))
    monkeypatch.setenv("FAKE_ARGS_OUT", str(tmp_path / "args.json"))
    monkeypatch.setenv("FAKE_MODULE", MOD)
    monkeypatch.setenv("SSX3_AGENT_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("SSX3_AGENT_SCRATCH", str(tmp_path / "scratch"))
    monkeypatch.setenv("SSX3_AGENT_BUDGET_USD", "50")
    monkeypatch.setenv("SSX3_OPENROUTER_API_KEY", "sk-or-test")
    return r


def run(repo, *extra):
    return dispatch.main([FN, "wave1", MOD, "--dossier", f"ref1/{FN}.md", *extra], repo=repo)


def test_parse_run_json_fixture():
    u = dispatch.parse_run_json(FIXTURE.read_text().splitlines())
    assert u.session_id == "ses_e6b310f99ffe3Fax0s97iI1K6M"
    assert u.cost_usd == pytest.approx(0.0011489)
    assert u.tokens_in == 61 + 79 + 40 + 59
    assert u.tokens_out == 50 + 66 + 55 + 63


def test_parse_run_json_without_steps_has_unknown_cost():
    u = dispatch.parse_run_json(FIXTURE.read_text().splitlines()[:1])
    assert u.cost_usd is None


def test_success_copies_module_back_and_logs(repo, capsys):
    assert run(repo) == 0
    assert (repo / MOD).read_text() == "// oc7 staging\n// ported\n"
    out = json.loads(capsys.readouterr().out)
    assert out["fn"] == FN and out["session"] == "ses_e6b310f99ffe3Fax0s97iI1K6M"
    [e] = ledger.read(Path(dispatch.os.environ["SSX3_AGENT_LEDGER"]))
    assert e.provider == "openrouter" and e.result == "pending" and e.cost_usd == pytest.approx(0.0011489)


def test_budget_block_exits_3(repo, tmp_path):
    now = datetime.now(timezone.utc).isoformat()
    ledger.append(tmp_path / "ledger.jsonl", ledger.Entry(now, "f_x", "w0", "openrouter", "m", 1, 1, 50.0, 1, "pass"))
    assert run(repo) == 3
    assert not (tmp_path / "args.json").exists()


def test_guard_reject_exits_4_and_cleans_worktree(repo, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_OPENCODE", "edit_two")
    assert run(repo) == 4
    assert (repo / MOD).read_text() == "// oc7 staging\n"
    assert (repo / "overrides.txt").read_text() == ""
    assert not any((tmp_path / "scratch").glob("wt-*"))


def test_opencode_failure_is_logged(repo, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_OPENCODE", "fail")
    assert run(repo) == 5
    [e] = ledger.read(tmp_path / "ledger.jsonl")
    assert e.result == "error"


def test_prompt_contains_upstream_writer_rules(repo, tmp_path):
    run(repo)
    prompt = json.loads((tmp_path / "args.json").read_text())[-1]
    assert "**One function, then stop.**" in prompt
    assert "Tick-rate pass" not in prompt
    assert MOD in prompt and f"ref1/{FN}.md" in prompt


def test_runs_standalone_with_writer_agent(repo, tmp_path):
    run(repo, "--model", "openrouter/deepseek/deepseek-chat")
    args = json.loads((tmp_path / "args.json").read_text())
    assert args[:2] == ["run", "--standalone"]
    assert args[args.index("-m") + 1] == "openrouter/deepseek/deepseek-chat"
    assert args[args.index("--agent") + 1] == "ssx3-writer"


def test_retry_reuses_session(repo, tmp_path):
    fb = tmp_path / "diff.txt"
    fb.write_text("generated v0=1, hand v0=2\n")
    run(repo, "--session", "ses_abc", "--feedback", str(fb), "--attempt", "2")
    args = json.loads((tmp_path / "args.json").read_text())
    assert args[args.index("--session") + 1] == "ses_abc"
    assert "generated v0=1, hand v0=2" in args[-1]


def test_writer_config_limits_edit_to_module():
    rules = dispatch.writer_config(MOD)["agents"]["ssx3-writer"]["permissions"]
    edits = [r for r in rules if r["action"] == "edit" and r["effect"] == "allow"]
    assert edits == [{"action": "edit", "resource": MOD, "effect": "allow"}]
    assert rules[0] == {"action": "*", "resource": "*", "effect": "deny"}


def test_missing_project_key_exits_6(repo, monkeypatch, tmp_path):
    monkeypatch.delenv("SSX3_OPENROUTER_API_KEY")
    assert run(repo) == 6
    assert not (tmp_path / "args.json").exists()


def test_writer_config_reads_project_key():
    assert dispatch.writer_config(MOD)["providers"]["openrouter"]["env"] == ["SSX3_OPENROUTER_API_KEY"]


SES = "ses_e6b310f99ffe3Fax0s97iI1K6M"


def test_isolated_data_dir_and_project_key(repo, tmp_path):
    run(repo)
    env = json.loads((tmp_path / "args.json.env").read_text())
    assert env["OPENROUTER_API_KEY"] == "sk-or-test"
    assert env["XDG_DATA_HOME"] == str(tmp_path / "scratch" / "opencode-data")


def test_retry_cost_is_delta_of_session_total(repo, monkeypatch, tmp_path):
    now = datetime.now(timezone.utc).isoformat()
    ledger.append(tmp_path / "ledger.jsonl", ledger.Entry(now, FN, "wave1", "openrouter", "m", 1, 1, 0.001, 1,
                                                          "fail", session=SES))
    monkeypatch.setenv("FAKE_COST", "0.003")
    assert run(repo, "--session", SES, "--attempt", "2") == 0
    last = ledger.read(tmp_path / "ledger.jsonl")[-1]
    assert last.session == SES and last.cost_usd == pytest.approx(0.002)


def test_export_failure_gives_unknown_cost(repo, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_EXPORT", "fail")
    run(repo)
    assert ledger.read(tmp_path / "ledger.jsonl")[-1].cost_usd is None


def test_writer_runs_in_standalone_clone(repo, tmp_path):
    # opencode resolves a git worktree to the main repo (config and edits would land there).
    run(repo)
    env = json.loads((tmp_path / "args.json.env").read_text())
    assert env["git_is_dir"] is True and env["has_config"] is True
    assert env["generated_link"] is True


def test_pwd_points_at_clone(repo, tmp_path):
    # opencode takes its project directory from $PWD, not the process cwd.
    run(repo)
    assert json.loads((tmp_path / "args.json.env").read_text())["pwd_matches_cwd"] is True


def test_clone_with_tracked_generated_metadata(repo, tmp_path):
    # Upstream tracks a few small files in generated/ (functions.tsv, ...) but not the shards, so
    # a checkout already has a generated/ directory: link the missing shards into it.
    (repo / "generated" / "functions.tsv").write_text("addr\tname\n")
    git(repo, "add", "-f", "generated/functions.tsv")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "track metadata")
    (repo / "generated" / "ee").mkdir()
    (repo / "generated" / "ee" / "s00.rs").write_text("// shard\n")
    assert run(repo) == 0
    env = json.loads((tmp_path / "args.json.env").read_text())
    assert env["generated_shard"] is True
