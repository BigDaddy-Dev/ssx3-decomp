#!/usr/bin/env python3
"""Stand-in for `opencode` in dispatcher tests. FAKE_OPENCODE selects the run behaviour."""
import json
import os
import sys
from pathlib import Path

FIXTURE = Path(__file__).with_name("opencode-run.jsonl")
args = sys.argv[1:]
if args[:2] == ["session", "export"]:
    if os.environ.get("FAKE_EXPORT") == "fail":
        sys.exit(1)
    print(json.dumps({"info": {"id": args[-1], "cost": float(os.environ.get("FAKE_COST", "0.0011489")),
                               "tokens": {"input": 239, "output": 234}}}))
    sys.exit(0)
mode = os.environ.get("FAKE_OPENCODE", "edit")
Path(os.environ["FAKE_ARGS_OUT"]).write_text(json.dumps(args))
Path(os.environ["FAKE_ARGS_OUT"] + ".env").write_text(json.dumps(
    {**{k: os.environ.get(k) for k in ("XDG_DATA_HOME", "OPENROUTER_API_KEY")},
     "git_is_dir": Path(".git").is_dir(), "has_config": Path("opencode.json").exists(),
     "generated_link": Path("generated").is_symlink(),
     "pwd_matches_cwd": os.environ.get("PWD") == os.getcwd()}))
lines = FIXTURE.read_text().splitlines()
module = Path(os.environ["FAKE_MODULE"])
if mode in ("edit", "edit_two"):
    module.write_text(module.read_text() + "// ported\n")
if mode == "edit_two":
    Path("overrides.txt").write_text("0x100000\n")
if mode == "fail":
    print("\n".join(lines[:3]))
    sys.exit(1)
print("\n".join(lines))
