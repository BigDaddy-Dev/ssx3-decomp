# Handover: start here

Read this first in a new session, then `state.md` (status, findings, log) and `orchestrator.md` (the
wave cycle in detail). Everything below was set up and verified on 2026-11-01.

## Where things are

| What | Where |
|---|---|
| Fork (this repo) | `~/Projects/ssx3-port` — origin `BigDaddy-Dev/ssx3-decomp`, upstream `andersfischernielsen/ssx3-decomp` |
| Spec + plan | retro-vault `docs/superpowers/{specs,plans}/2026-11-01-ssx3-native-port*.md` |
| C++ reference decomp | `~/Projects/devvydont-ssx3` (`SSX3_REF`) |
| Secrets + paths | `.envrc` (git-excluded): `SSX3_ISO`, `SSX3_REF`, `SSX3_OPENROUTER_API_KEY`, `JAVA_HOME`, cargo. Never print the key. |
| Writer cost ledger | `tools/agents/ledger.jsonl` (git-excluded); `python3 tools/agents/ledger.py status` |
| Scratch for writers | `.agents-wt/` (clones, logs, diffs, one opencode data dir per function) |
| Wave working files | `out/waveN/` (profile, lanes, dossiers, feedback) — git-excluded |
| PCSX2 comparison | `tools/pcsx2-diff/run.py` (see `pcsx2-comparison.md`, `run.py --help`) |
| Ghidra + GhidraMCP | retro-vault `library/tools/ghidra/`; `.mcp.json` (git-excluded) |

## Branches and what gets merged (agreed 2026-11-01)

- **`main`** mirrors upstream and only ever fast-forwards from `upstream/main`. Nothing local is
  merged into it. Ported functions reach it only after upstream merges our PR.
- **`tooling`** is our workbench (dispatcher, ledger, guards, hooks, pcsx2-diff, `docs/local`). It is
  never merged into `main`; rebase it onto `main` after each sync. Pushed to origin as a backup.
- **`wave-N`** is cut from `tooling` for one wave. Tooling fixes made during a wave are
  cherry-picked onto `tooling` at the end of it.
- **`upstream-pr/<name>`** is cut from `main` and holds only project work: verified ports (difftest
  and RAM gate green, reorganised as upstream does) or a small generic change. A PR is opened only on
  the user's explicit yes, every time.
- Never committed anywhere: `Cargo.lock` churn, game material (`orig/`, `generated/`, ISO, RAM/VRAM
  dumps, savestates; the pre-commit hook blocks these), ledger rows, dossiers, profiles, failed
  writer output.
- Fork commits carry **no Co-Authored-By line** (upstream rule).

## The wave cycle (one wave ≈ one session)

1. **Sync** `main` (ff from upstream), `git rebase main tooling`, `git switch -c wave-N tooling`.
2. **Pick** profile → `pick_wave.py` → 12 hottest unported functions → 4 lanes (`ocM`…`ocM+3`, 3
   each) → `refdossier2.py` dossiers → commit the empty staging modules.
3. **Write** 4 lanes in parallel, sequential within a lane (`write-one.sh`).
4. **Verify** each function's difftest; failures → same-session retry with the exact error (≤2) →
   Claude subagent → skip with a note. `ledger.py mark` every result.
5. **Install** `integrate_wave.py all` (gate must print "identical"), `reorg_modules.py`, gate again.
6. **Compare** `run.py p1_race_snow_jam` (native side automated); PCSX2 side only when needed.
7. **Close** ledger stats + `state.md`; tooling fixes → `tooling`; cut `upstream-pr/wave-N` with the
   port commits only; ask the user before opening the PR.

Heavy processes (cargo build/test, game runs) always go through `flock target/.heavy.lock …` —
15 GB RAM.

## Current position (end of the setup session)

- P0–P2 done: build + upstream tests, guard hooks, dispatcher, ledger, state-trace hook, PCSX2 PINE,
  `.p2m2` playback, comparison runner (34 tests). Ghidra GUI analysis and the native playtest are
  still open (need the user's desktop).
- **Wave 1 is mid-cycle**: writer output for 12 functions is committed on `wave-1` as
  *unverified*. Resume at step 4 (verify). `RiderSpinSub_HandleInput` attempt 1 failed (brace
  mismatch, no test); its feedback is in `out/wave1/fb-RiderSpinSub_HandleInput-1.txt`.
- **`upstream-pr/state-trace`** is ready and verified on its own (the `SSX3_STATE_TRACE` hook alone,
  cut from `main`: build OK, RAM gate identical, `state_trace` tests 2/2). Worktree
  `~/Projects/ssx3-port-pr`; PR text in `docs/local/pr-state-trace.md`. Not pushed; waiting for the
  user's yes to push it and open the PR.
- Budget: $50/month OpenRouter cap; first function cost $0.15 (~594k input tokens), so watch cost
  per passed function after wave 1 and apply the switching rule in `orchestrator.md`.

## Open findings

- **Start-grid divergence:** native vs PCSX2 first differ at race frame 1 (AI riders 4/5 grid
  positions ~26 units apart); riders 0–3 match until ~frame 200. Suspect an RNG/timer difference
  before the race.
- **10× timers:** always-on counters (`EA_TIMER_TICKS` 0x450dcc, `APPMAN_VSYNC` 0x4c9440, …) rise
  +1 per vsync in PCSX2 but +10 per headless frame natively. Likely related to the above; worth an
  upstream issue (only with the user's yes).

## Naming

Follow upstream: lowercase kebab-case for docs and tool folders (`docs/local/state.md`,
`tools/pcsx2-diff/`), snake_case for Python modules; only `README.md`/`AGENTS.md` are uppercase.

## Working with the user

- They play on the desktop via Sunshine streaming: keyboard shortcuts and controller menus don't
  reach PCSX2 menus. Drive PCSX2 with `xdotool` on `DISPLAY=:0` (env from the `plasmashell`
  process) and check with `import -window root` screenshots; launch PCSX2 with `-nofullscreen`.
- Outward actions (push, PR, issue) need a fresh yes each time.
