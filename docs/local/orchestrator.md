# Orchestrator runbook (porting waves with opencode writers)

Upstream's `AGENTS.md` porting loop is the authority. This runbook changes it in three places only, and
adds the local plumbing.

## Before a wave

- `. ./.envrc` (sets `SSX3_ISO`, `SSX3_REF`, `SSX3_OPENROUTER_API_KEY`, `JAVA_HOME`, cargo on `PATH`).
- One heavy process at a time: wrap every cargo build/test and game run in
  `flock target/.heavy.lock …` (another agent may share the machine).
- `python3 tools/agents/ledger.py status` must say the budget is OK.
- Branches and merge rules: see `HANDOVER.md`. In short: `wave-N` from `tooling`; upstream PRs are
  cut onto `upstream-pr/wave-N` from `main` with only the port commits (no `docs/local`, no
  `tools/agents`, no `tools/pcsx2-diff`); `main` only fast-forwards from upstream.

## The loop (upstream steps, with the three changes)

1. **Pick** 12 functions (4 lanes × 3) as upstream says: a fresh profile
   (`CARGO_TARGET_DIR=target-prof cargo build --profile game -p ssx3 --bin ssx3-headless --features callprof`,
   then a race replay with `SSX3_CALLPROF=<out>:<from>:<to>`), `tools/pick_wave.py`, dossiers with
   `tools/refdossier2.py` (`pick_wave.py EDGES OUTDIR N MOD` — N is the wave number, it writes 50 per
   module; take the top 12 and split them round-robin into lanes). Create the staging module `crates/ssx3-game/src/ocM.rs` (the empty `OVERRIDES`
   skeleton from the worker guide) and wire it: `ocM = []` in `[features]` and the `packages` list of
   `crates/ssx3-game/Cargo.toml`, `#[cfg(feature = "ocM")] pub mod ocM;` and its `OVERRIDES` extend in
   `lib.rs`. Commit the skeleton so writer clones see it.
2. **Writers — change 1:** a writer is `tools/agents/write-one.sh <fn> waveN crates/ssx3-game/src/ocM.rs
   --dossier refN/<fn>.md`, not a Claude subagent. At most four at once, **one function per writer, in the
   same module file — so run them one after another for one module, or give each writer its own module**
   (`ocM`, `ocM+1`, …) when running in parallel. Writers never build.
3. **Verify — change 2:** run the module test yourself (`SSX3_DIFF_STRICT=args cargo test --profile game
   -p ssx3-game --features ocM --lib ocM::`). Mechanical compile errors: fix directly. Semantic or fixture
   failures: write the exact generated-vs-hand diff to a file and rerun
   `write-one.sh … --feedback <file> --session <id> --attempt 2` (the same model; at most 2 retries).
   Still failing: a **Claude subagent** gets upstream's writer rules, the dossier and the failure history;
   log it with `provider="claude"`. Still failing: upstream rule 7 (skip with a note).
   Record every result: `python3 tools/agents/ledger.py mark <fn> <attempt> pass|fail`.
4. **Install** green modules exactly as upstream (`integrate_wave.py prep/regen/repoint/test/build/gate`,
   gate must print `GATE: race replay RAM identical to the baseline`, then `reorg_modules.py apply ocM`,
   test and gate again). Commit with upstream's style, **no Co-Authored-By line**.
5. **Browser form** smoke check, as upstream step 5.

## After each wave — change 3

- `python3 tools/agents/ledger.py status`. **Switching rule:** first-try pass rate under 30% over the
  wave, or OpenRouter cost per passed function above Claude's → start the next wave Claude-first.
- `python3 tools/pcsx2-diff/run.py p1_race_snow_jam` (when the runner exists) and look at the trend in
  `tools/pcsx2-diff/history.jsonl`; an earlier first divergence → `tools/bisect_overrides.py`.
- Update `docs/local/STATE.md` (pass rates, cost, next wave).

## Recovering the budget gate

An OpenRouter call with an unknown cost (`cost_usd: null`) stops all writers. Look the session up on the
OpenRouter activity page (project key's account), put the real cost into that ledger line, and continue.

## Closing a wave

1. `ledger.py status` → wave numbers into `STATE.md` (passed / skipped / cost per passed function).
2. Tooling fixes made on `wave-N` → `git cherry-pick` onto `tooling`.
3. `git switch -c upstream-pr/wave-N main` and cherry-pick only the installed-and-reorganised port
   commits; build, test and gate on that branch; draft the PR text in `docs/local/`.
4. Ask the user before pushing it or opening the PR.
