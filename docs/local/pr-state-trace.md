# Draft PR: headless per-frame state trace (`SSX3_STATE_TRACE`)

Branch: `upstream-pr/state-trace` (one commit on `main`). Open only on the user's yes.

**Title:** Add SSX3_STATE_TRACE: per-frame RAM ranges from the headless runner

**Body:**

`ssx3-headless` can already dump all of EE RAM at exit (`SSX3_RAM_DUMP`). This adds a cheap way to
record a few chosen ranges on every frame (or every n-th), for following game state over a run
rather than only at its end — for example to compare rider positions frame by frame against
another source of truth, or to find the first frame where a change makes a replay drift.

- `SSX3_STATE_TRACE=<file>` turns it on; `SSX3_STATE_RANGES=0xADDR+LEN,...` picks the ranges;
  `SSX3_STATE_EVERY=n` samples every n-th frame (default 1).
- Each record is the frame number (u32 LE) followed by the bytes of each range in order. Writes are
  unbuffered so a killed run still leaves complete records.
- Off by default; with the variable unset nothing changes (the race-replay gate is identical).

Tests: `crates/ssx3/tests/state_trace.rs` (ignored like the other disc-needing tests):
`scenarios_trace_matches_ram_dump` checks the traced bytes against `SSX3_RAM_DUMP` at the same
frame; `no_trace_without_env` checks nothing is written when it's off.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
