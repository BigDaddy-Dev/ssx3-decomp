#!/usr/bin/env python3
"""L3 differential runner: one upstream scenario, native build vs PCSX2, compared per race frame.

  python3 tools/pcsx2-diff/run.py prepare SCENARIO       # per-side inputs + the .p2m2 for PCSX2
  python3 tools/pcsx2-diff/run.py sample-pcsx2 SCENARIO  # sample a PCSX2 playback over PINE
  python3 tools/pcsx2-diff/run.py SCENARIO [--pcsx2-samples FILE] [--pcsx2-race-start N]

Both sides reach the race at different boot frames (native loads are instant), so the scenario script
is split: menu presses stay timed from boot, riding presses are moved per side so they land on the same
race frames (l3/script.py). Race starts: native measured by a run that dumps RAM at the end; PCSX2 from
race_start.json (or --pcsx2-race-start), recorded once from a playback (end boot frame - race frame).

PCSX2 playback has no command line: after `prepare`, load out/pcsx2-diff/SCENARIO/pcsx2.p2m2 in PCSX2
(Tools -> Input Recording -> Play), then run `sample-pcsx2` while it plays. Every game run takes the
heavy-process lock (SSX3_HEAVY_LOCK, default ~/Projects/ssx3-port/target/.heavy.lock).

Outputs: out/pcsx2-diff/SCENARIO/{native.input,pcsx2.input,pcsx2.p2m2,pcsx2-samples.jsonl} and
out/pcsx2-diff/SCENARIO/COMMIT/report.md; one line per comparison in tools/pcsx2-diff/history.jsonl.
"""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l3.compare import after_last_reset, first_divergence  # noqa: E402
from l3.fields import load_fields, ranges, resolve  # noqa: E402
from l3.inputs import scenario_to_p2m2  # noqa: E402
from l3.native import dump_reader, race_start, read_trace  # noqa: E402
from l3.report import append_history, make_record, write_report  # noqa: E402
from l3.script import gameplay_start, parse_script, per_side_script  # noqa: E402

REPO = HERE.parents[1]
FIELDS = HERE / "fields.toml"
RACE_STARTS = HERE / "race_start.json"
HISTORY = HERE / "history.jsonl"
DEFAULT_BIN = REPO / "target" / "release" / "ssx3-headless"
DEFAULT_LOCK = Path.home() / "Projects" / "ssx3-port" / "target" / ".heavy.lock"
FRESH_RACE = 120  # sample-pcsx2 starts on a race whose counter is still below this


def scenario(name):
    run = lambda *a: subprocess.run([sys.executable, str(REPO / "tools" / "scenarios.py"), *a, name],
                                    check=True, capture_output=True, text=True, cwd=REPO).stdout.strip()
    return run("input"), int(run("frames")), run("card")


def outdir(name):
    d = REPO / "out" / "pcsx2-diff" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def pcsx2_race_start(name, override):
    if override is not None:
        return override
    starts = json.loads(RACE_STARTS.read_text()) if RACE_STARTS.exists() else {}
    if name not in starts:
        sys.exit(f"no PCSX2 race start for {name}: record it in {RACE_STARTS.name} or pass --pcsx2-race-start")
    return starts[name]["pcsx2"]


class heavy_lock:
    def __enter__(self):
        path = Path(os.environ.get("SSX3_HEAVY_LOCK", DEFAULT_LOCK))
        path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(path, "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)

    def __exit__(self, *exc):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def run_native(binary, frames, script, card, work, extra_env):
    if not os.environ.get("SSX3_ISO"):
        sys.exit("SSX3_ISO is unset: the headless runner idles at boot without it (source .envrc)")
    copy = work / "card.ps2"
    if card != "fresh":
        shutil.copy(REPO / card, copy)
    elif copy.exists():
        copy.unlink()
    env = dict(os.environ, SSX3_INPUT=script, SSX3_MEMCARD=str(copy), **extra_env)
    with heavy_lock():
        r = subprocess.run([str(binary), str(frames)], cwd=REPO, env=env, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"native run failed ({r.returncode}):\n{r.stderr[-2000:]}")


def prepare(name, pcsx2_rs, binary, margin):
    """Measure the native race start, then write both sides' inputs. Returns the plan."""
    inp, frames, card = scenario(name)
    presses = parse_script(inp)
    if gameplay_start(presses) is None:
        sys.exit(f"{name} never rides: menus are compared end-of-run only (not implemented yet)")
    d = outdir(name)
    fields = load_fields(FIELDS)
    frame_field = next(f for f in fields if f.name == "frame")
    dump = d / "native-race-start.ram"
    run_native(binary, frames, inp, card, d, {"SSX3_RAM_DUMP": str(dump)})
    ram = dump.read_bytes()
    native_rs = race_start(dump_reader(ram), frame_field, frames)
    dump.unlink()  # 32 MiB of game RAM: never kept
    race_len = frames - pcsx2_rs
    plan = {"scenario": name, "card": card, "frames": frames, "margin": margin,
            "native_race_start": native_rs, "pcsx2_race_start": pcsx2_rs, "race_frames": race_len,
            "native_frames": native_rs + race_len}
    (d / "native.input").write_text(per_side_script(presses, native_rs, pcsx2_rs, margin))
    pcs = per_side_script(presses, pcsx2_rs, pcsx2_rs, margin)
    (d / "pcsx2.input").write_text(pcs)
    scenario_to_p2m2(pcs, frames, d / "pcsx2.p2m2")
    (d / "plan.json").write_text(json.dumps(plan, indent=1))
    return plan


def sample_pcsx2(name, out, race_frames, idle_s=5.0):
    from l3.pcsx2 import Pcsx2Sampler
    s = Pcsx2Sampler()
    s.check_game()
    fields = load_fields(FIELDS)
    print("waiting for the race (start the .p2m2 playback in PCSX2)...", file=sys.stderr)
    while True:  # a race from an earlier playback can still be in memory: wait for a fresh one
        try:
            live = resolve(fields, lambda a: s.pine.read(a, 4))
            if s.sample(live[:1])["frame"][0] <= FRESH_RACE:
                break
        except ValueError:
            pass
        time.sleep(0.1)
    n, last, last_t = 0, None, time.time()
    with open(out, "w") as f:
        # The counter holds at 0 through the pre-race intro: only time out once it has moved.
        while not last or time.time() - last_t < idle_s:
            row = s.sample(live)
            fr = row["frame"][0]
            if fr != last:
                f.write(json.dumps(row) + "\n")
                n, last, last_t = n + 1, fr, time.time()
                if fr >= race_frames:
                    break
    print(f"{n} samples, last race frame {last}", file=sys.stderr)


def git_commit():
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def compare(name, plan, binary, pcsx2_samples):
    d = outdir(name)
    fields = load_fields(FIELDS)
    frame_field = next(f for f in fields if f.name == "frame")
    # Resolve the chains from a dump inside this race, then trace those addresses every frame.
    dump = d / "native-chains.ram"
    script = (d / "native.input").read_text()
    run_native(binary, plan["native_frames"], script, plan["card"], d, {"SSX3_RAM_DUMP": str(dump)})
    read32 = dump_reader(dump.read_bytes())
    dump.unlink()
    live = resolve(fields, read32)
    rs = race_start(read32, frame_field, plan["native_frames"])
    if rs != plan["native_race_start"]:
        sys.exit(f"native race start moved ({plan['native_race_start']} -> {rs}) after re-timing")
    trace = d / "native-trace.bin"
    run_native(binary, plan["native_frames"], script, plan["card"], d,
               {"SSX3_STATE_TRACE": str(trace), "SSX3_STATE_RANGES": ranges(live), "SSX3_STATE_EVERY": "1"})
    native = after_last_reset([r for r in read_trace(trace, live) if r["_sample_frame"] > rs])
    trace.unlink()
    with open(d / "native-samples.jsonl", "w") as f:  # same shape as pcsx2-samples.jsonl, for digging
        f.writelines(json.dumps(r) + "\n" for r in native)
    pcsx2 = after_last_reset([json.loads(l) for l in Path(pcsx2_samples).read_text().splitlines() if l.strip()])
    div = first_divergence(native, pcsx2, live)
    commit = git_commit()
    rd = d / commit
    rd.mkdir(exist_ok=True)
    common = len({r["frame"][0] for r in native} & {r["frame"][0] for r in pcsx2})
    meta = {**{k: plan[k] for k in ("native_race_start", "pcsx2_race_start", "race_frames")},
            "native samples": len(native), "pcsx2 samples": len(pcsx2), "race frames compared": common,
            "binary": binary}
    write_report(rd / "report.md", name, commit, div, meta)
    append_history(HISTORY, make_record(commit, name, "per-frame", div))
    return div, common, rd / "report.md"


def main(argv):
    if argv[:1] in (["prepare"], ["sample-pcsx2"]):
        cmd, argv = argv[0], argv[1:]
    else:
        cmd = "compare"
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario")
    ap.add_argument("--pcsx2-race-start", type=int)
    ap.add_argument("--pcsx2-samples", help="samples from `sample-pcsx2` (default: the scenario's out dir)")
    ap.add_argument("--bin", default=os.environ.get("SSX3_HEADLESS", DEFAULT_BIN))
    ap.add_argument("--margin", type=int, default=0, help="drop menu presses this close to race start")
    a = ap.parse_args(argv)
    d = outdir(a.scenario)
    if cmd == "prepare":
        print(json.dumps(prepare(a.scenario, pcsx2_race_start(a.scenario, a.pcsx2_race_start), a.bin, a.margin)))
        print(f"now play {d / 'pcsx2.p2m2'} in PCSX2 and run: run.py sample-pcsx2 {a.scenario}", file=sys.stderr)
    elif cmd == "sample-pcsx2":
        plan = json.loads((d / "plan.json").read_text())
        sample_pcsx2(a.scenario, d / "pcsx2-samples.jsonl", plan["race_frames"])
    else:
        samples = Path(a.pcsx2_samples or d / "pcsx2-samples.jsonl")
        if not samples.exists():
            sys.exit(f"no PCSX2 samples at {samples}: run `run.py sample-pcsx2 {a.scenario}` during playback")
        plan_p = d / "plan.json"
        plan = json.loads(plan_p.read_text()) if plan_p.exists() else \
            prepare(a.scenario, pcsx2_race_start(a.scenario, a.pcsx2_race_start), a.bin, a.margin)
        div, common, report = compare(a.scenario, plan, a.bin, samples)
        print(f"{report}: " + (f"first divergence at race frame {div.frame} ({', '.join(sorted(div.fields))})"
                               if div else f"no divergence over {common} race frames"))


if __name__ == "__main__":
    main(sys.argv[1:])
