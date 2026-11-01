# SSX 3 native port: local state

Fork of andersfischernielsen/ssx3-decomp. Spec and plan live in retro-vault:
`docs/superpowers/specs/2026-11-01-ssx3-native-port-design.md`,
`docs/superpowers/plans/2026-11-01-ssx3-native-port.md`.

Start of session: `. ./.envrc` (sets `CARGO_BUILD_JOBS=6`, `SSX3_ISO`, cargo on `PATH`).
One heavy process at a time (a build or a game run).

## Status
- P0 Setup: in progress. ISO checksum OK (2026-11-01).
- P1 Linux playability: not started.
- P2 PCSX2 comparison: not started.
- P3 Agent porting: not started.

## Blockers
- (none)

## Session log
- 2026-11-01: forked to BigDaddy-Dev/ssx3-decomp, cloned to ~/Projects/ssx3-port, `setup.py` OK
  (13,306 functions, 55.8 MB generated Rust). Next: first build and upstream tests.
