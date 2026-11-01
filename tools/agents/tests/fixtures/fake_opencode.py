#!/usr/bin/env python3
"""Stand-in for `opencode run` in dispatcher tests. FAKE_OPENCODE selects the behaviour."""
import json
import os
import sys
from pathlib import Path

FIXTURE = Path(__file__).with_name("opencode-run.jsonl")
mode = os.environ.get("FAKE_OPENCODE", "edit")
Path(os.environ["FAKE_ARGS_OUT"]).write_text(json.dumps(sys.argv[1:]))
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
