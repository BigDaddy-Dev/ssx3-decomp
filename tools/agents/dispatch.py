#!/usr/bin/env python3
"""Run one writer (opencode + an OpenRouter model) on one function, in a scratch clone.

  tools/agents/write-one.sh <fn> <wave> <module> --dossier refN/<fn>.md
                            [--model M] [--feedback FILE] [--session ID] [--attempt N]

Exit 0: the module file was copied back into this tree; prints JSON {fn, model, session, attempt,
report, diff_path}. Exit 3: budget blocked (opencode never ran). Exit 4: the writer touched more than
its module (nothing copied back). Exit 5: opencode failed or timed out. Exit 6: SSX3_OPENROUTER_API_KEY unset. Every call is in the ledger;
the orchestrator records the test result later with `ledger.py mark`.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402
import ledger  # noqa: E402

# The user's pick first; the order is revisited from measured pass rates (ledger.py status).
DEFAULT_MODELS = ["openrouter/deepseek/deepseek-v4.1-flash-1017", "openrouter/qwen/qwen3-coder"]
TIMEOUT_S = 15 * 60
KEY_ENV = "SSX3_OPENROUTER_API_KEY"  # this project's own OpenRouter key (set in .envrc, never committed)


@dataclass
class Usage:
    tokens_in: int
    tokens_out: int
    cost_usd: float | None
    session_id: str
    final_text: str


def parse_run_json(lines):
    session, text, cost, tin, tout, steps = "", "", 0.0, 0, 0, 0
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        session = session or ev.get("sessionID", "")
        part = ev.get("part", {})
        if ev.get("type") == "text":
            text = part.get("text", text)
        elif ev.get("type") == "step_finish":
            steps += 1
            cost += part.get("cost", 0.0)
            tin += part.get("tokens", {}).get("input", 0)
            tout += part.get("tokens", {}).get("output", 0)
    return Usage(tin, tout, round(cost, 10) if steps else None, session, text.strip())


def session_cost(opencode, sid, env):
    """Cumulative (cost, tokens_in, tokens_out) of an opencode session, or None if it can't be read.

    The run's own JSON omits the last step's usage, so the session export is the source of truth.
    """
    try:
        p = subprocess.run([opencode, "session", "export", "--standalone", sid], env=env,
                           capture_output=True, text=True, timeout=120)
        info = json.loads(p.stdout)["info"] if p.returncode == 0 else None
    except (subprocess.TimeoutExpired, ValueError, KeyError):
        info = None
    if not info or "cost" not in info:
        return None
    t = info.get("tokens", {})
    return float(info["cost"]), t.get("input", 0), t.get("output", 0)


def writer_rules(agents_md):
    out, on = [], False
    for line in agents_md.splitlines():
        if line.startswith("### Subagent (writer)"):
            on = True
            continue
        if on and line.strip() == "---":
            break
        if on:
            out.append(line)
    if not out:
        raise SystemExit("AGENTS.md has no '### Subagent (writer)' section")
    return "\n".join(out).strip()


def writer_config(module):
    allow = lambda a, r="*": {"action": a, "resource": r, "effect": "allow"}  # noqa: E731
    return {
        "$schema": "https://opencode.ai/config.json",
        "providers": {"openrouter": {"env": [KEY_ENV]}},
        "agents": {"ssx3-writer": {
            "mode": "primary",
            "description": "SSX 3 port writer: edits one module file, never builds",
            "steps": 80,
            "permissions": [
                {"action": "*", "resource": "*", "effect": "deny"},
                allow("read"), allow("glob"), allow("grep"), allow("list"),
                allow("edit", module),
            ],
        }},
    }


def _git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, text=True).stdout


def _changes(wt):
    out = [tuple(l.split("\t", 1)) for l in _git(wt, "diff", "--name-status").splitlines() if l]
    out += [("A", p) for p in _git(wt, "ls-files", "--others", "--exclude-standard").splitlines() if p]
    return out


def main(argv, repo=None):
    ap = argparse.ArgumentParser(prog="write-one.sh")
    ap.add_argument("fn")
    ap.add_argument("wave")
    ap.add_argument("module")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--model", default=DEFAULT_MODELS[0])
    ap.add_argument("--feedback")
    ap.add_argument("--session")
    ap.add_argument("--attempt", type=int, default=1)
    a = ap.parse_args(argv)
    repo = Path(repo or _git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    ledger_path = Path(os.environ.get("SSX3_AGENT_LEDGER", HERE / "ledger.jsonl"))
    now = datetime.now(timezone.utc)

    if a.model.startswith("openrouter/") and not os.environ.get(KEY_ENV):
        print(f"write-one: {KEY_ENV} is not set; put the project's OpenRouter key in .envrc", file=sys.stderr)
        return 6

    ok, msg = ledger.budget_ok(ledger.read(ledger_path), now, float(os.environ.get("SSX3_AGENT_BUDGET_USD", "50")))
    if not ok:
        print(f"write-one: {msg}", file=sys.stderr)
        return 3

    feedback = ""
    if a.feedback:
        feedback = ("\nYour previous attempt failed its differential test. The exact generated-vs-hand "
                    "difference:\n\n" + Path(a.feedback).read_text() + "\nFix the port, keep the test.\n")
    prompt = Template((HERE / "prompt.md.tmpl").read_text()).substitute(
        fn=a.fn, wave=a.wave, module=a.module, dossier=a.dossier,
        rules=writer_rules((repo / "AGENTS.md").read_text()), feedback=feedback)

    scratch = Path(os.environ.get("SSX3_AGENT_SCRATCH", repo / ".agents-wt"))
    scratch.mkdir(parents=True, exist_ok=True)
    wt = scratch / f"wt-{a.fn}"
    # A standalone clone, not a git worktree: opencode resolves a worktree to the main repo, which
    # would load the wrong config and let edits land in the orchestrator's tree.
    shutil.rmtree(wt, ignore_errors=True)
    head = _git(repo, "rev-parse", "HEAD").strip()
    _git(scratch, "clone", "-q", "--shared", "--no-checkout", str(repo), str(wt))
    _git(wt, "checkout", "-q", "--detach", head)
    if (repo / "generated").is_dir():  # read-only use; edit permission covers the module only
        # Link what the checkout lacks: all of generated/, or (when upstream tracks a few metadata
        # files there) just the untracked entries such as the ee/ shards. A symlink is a file to
        # git, so exclude each link by exact path (/x/ would not match it).
        if (wt / "generated").exists():
            links = [(wt / "generated" / p.name, p) for p in (repo / "generated").iterdir()
                     if not (wt / "generated" / p.name).exists()]
        else:
            links = [(wt / "generated", repo / "generated")]
        with open(wt / ".git" / "info" / "exclude", "a") as f:
            for link, target in links:
                link.symlink_to(target, target_is_directory=target.is_dir())
                f.write(f"/{link.relative_to(wt).as_posix()}\n")

    opencode = os.environ.get("OPENCODE_BIN", "opencode")
    env = dict(os.environ)
    # A data dir of our own: opencode prefers its stored login over OPENROUTER_API_KEY, and the
    # project key must be the only credential a writer can spend.
    # One per function: parallel standalone servers sharing a data dir fail to start, and a retry
    # (--session) must find its session again.
    env["XDG_DATA_HOME"] = str(scratch / "opencode-data" / a.fn)
    if os.environ.get(KEY_ENV):
        env["OPENROUTER_API_KEY"] = os.environ[KEY_ENV]

    def log(usage, result):
        sid = usage.session_id or a.session or ""
        cost, tin, tout = None, usage.tokens_in, usage.tokens_out
        total = session_cost(opencode, sid, env) if sid else None
        if not sid:  # opencode never started a session, so no model call was made
            cost = 0.0
        if total is not None:
            before = sum(x.cost_usd or 0.0 for x in ledger.read(ledger_path) if sid and x.session == sid)
            cost, tin, tout = round(max(total[0] - before, 0.0), 10), total[1], total[2]
        ledger.append(ledger_path, ledger.Entry(
            ts=now.isoformat(), fn=a.fn, wave=a.wave, provider=a.model.split("/")[0], model=a.model,
            tokens_in=tin, tokens_out=tout, cost_usd=cost, attempt=a.attempt, result=result, session=sid))

    try:
        for rel in (a.module, a.dossier):
            if (repo / rel).exists():
                (wt / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repo / rel, wt / rel)
        (wt / "opencode.json").write_text(json.dumps(writer_config(a.module), indent=1))
        _git(wt, "add", "-A", "-f", "--", *[p for p in (a.module, a.dossier, "opencode.json") if (wt / p).exists()])

        cmd = [opencode, "run", "--standalone", "-m", a.model,
               "--agent", "ssx3-writer", "--format", "json", "--auto", "--title", f"{a.wave} {a.fn}"]
        if a.session:
            cmd += ["--session", a.session]
        cmd.append(prompt)
        try:
            # opencode resolves its project from $PWD, which cwd= alone leaves pointing at the caller.
            p = subprocess.run(cmd, cwd=wt, env={**env, "PWD": str(wt)}, capture_output=True, text=True, timeout=TIMEOUT_S)
            stdout, failed = p.stdout, p.returncode != 0
            (scratch / f"{a.fn}-attempt{a.attempt}.log").write_text(p.stderr or "")
        except subprocess.TimeoutExpired as e:
            stdout, failed = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), True
        usage = parse_run_json(stdout.splitlines())
        if failed:
            log(usage, "error")
            log_path = scratch / f"{a.fn}-attempt{a.attempt}.log"
            tail = log_path.read_text()[-800:] if log_path.exists() else "(timed out)"
            print(f"write-one: opencode failed or timed out for {a.fn}; log {log_path}:\n{tail}", file=sys.stderr)
            return 5

        problems = guard.check_diff(_changes(wt), a.module)
        if problems:
            log(usage, "rejected")
            print("write-one: rejected:\n  " + "\n  ".join(problems), file=sys.stderr)
            return 4

        diff_path = scratch / f"{a.fn}-attempt{a.attempt}.diff"
        diff_path.write_text(_git(wt, "diff"))
        (repo / a.module).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wt / a.module, repo / a.module)
        log(usage, "pending")
        print(json.dumps({"fn": a.fn, "model": a.model, "session": usage.session_id, "attempt": a.attempt,
                          "report": usage.final_text, "diff_path": str(diff_path)}))
        return 0
    finally:
        shutil.rmtree(wt, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
