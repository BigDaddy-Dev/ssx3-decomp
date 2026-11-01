# SSX 3 native port: local state

Fork of andersfischernielsen/ssx3-decomp. Spec and plan live in retro-vault:
`docs/superpowers/specs/2026-11-01-ssx3-native-port-design.md`,
`docs/superpowers/plans/2026-11-01-ssx3-native-port.md`.

Start of session: `. ./.envrc` (sets `CARGO_BUILD_JOBS=6`, `SSX3_ISO`, cargo on `PATH`).
One heavy process at a time (a build or a game run).

## Status
- P0 Setup: build + upstream tests OK (183 passed). Ghidra 12.1.4 + EE plugin + LaurieWired GhidraMCP 2.0
  installed in retro-vault `library/tools/ghidra/`; PCSX2 PINE on (slot 28011). GUI checks pending.
- P1 Linux playability: launcher in ES-DE Ports ("SSX 3 (Native)"); playtest not started.
- P2 PCSX2 comparison: trace hook (`SSX3_STATE_TRACE`) in, gate green; pcsx2-diff core in;
  `.p2m2` layout in `docs/local/l3-spike.md`. Needs: PINE during playback, frame-counter address,
  `fields.toml`, the runner (`run.py`).
- P3 Agent porting: ledger, guard, dispatcher done; real end-to-end writer run OK (DeepSeek V4.1 Flash,
  $0.0026). Needs: orchestrator runbook and the first real wave.

## Blockers
- GUI steps need the user at the desktop (this shell has no display): Ghidra import + analysis,
  `pine.py info` with SSX 3 booted in PCSX2, playtest, `.p2m2` playback test.

## Gotchas
- opencode v2: run writers with `--standalone`; it takes its project from `$PWD`; a git worktree
  resolves to the main repo; its stored login beats `OPENROUTER_API_KEY` unless `XDG_DATA_HOME` is
  isolated; the run JSON omits the last step's cost (use `opencode session export`).
- `Cargo.lock` shows as modified after a local build (newer cargo); don't commit it.
- Gate baseline lives in `target/gate/base/ds1.bin` (created 2026-11-01 from the unchanged tree).

## Session log
- 2026-11-01: forked to BigDaddy-Dev/ssx3-decomp, cloned to ~/Projects/ssx3-port, `setup.py` OK
  (13,306 functions, 55.8 MB generated Rust). Next: first build and upstream tests.
- 2026-11-01 (later): toolchain, pre-commit guard, ledger, guard, dispatcher (real run OK), trace
  hook (gate green), pcsx2-diff core, Ghidra/PINE installs. Next: user GUI checks (Task 2), playtest
  (Task 4), L3 feasibility steps 2–4 (Task 5), then fields.toml, runner, runbook and first wave.
