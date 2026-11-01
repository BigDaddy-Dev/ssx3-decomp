# L3 feasibility (Task 5): decision record

Source of truth: PCSX2 v2.8.2, `pcsx2/Recording/InputRecordingFile.{h,cpp}` and `PadData.cpp`.

## 1. `.p2m2` layout (read from source, 2026-11-01)

All integers little-endian. Header is 570 bytes:

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | file version = `1` |
| 1 | 50 | emulator version, NUL-padded (`PCSX2-<gitrev>`) |
| 51 | 255 | author, NUL-padded |
| 306 | 255 | game name, NUL-padded |
| 561 | 4 | total frames (u32) |
| 565 | 4 | undo count (u32) |
| 569 | 1 | from savestate (bool) |

Frame `f` starts at `570 + f * 36`: two ports × 18 bytes (port 0 first, then port 1).

The 18 bytes for one pad:

| Byte | Meaning |
|---|---|
| 0 | buttons group one, **active low**: bit7 Left, 6 Down, 5 Right, 4 Up, 3 Start, 2 R3, 1 L3, 0 Select |
| 1 | buttons group two, **active low**: bit7 Square, 6 Cross, 5 Circle, 4 Triangle, 3 R1, 2 L1, 1 R2, 0 L2 |
| 2, 3 | right analog x, y |
| 4, 5 | left analog x, y |
| 6–9 | pressure: Right, Left, Up, Down |
| 10–13 | pressure: Triangle, Circle, Cross, Square |
| 14–17 | pressure: L1, R1, L2, R2 |

**Mapping from upstream's libpad bitmask** (`tools/scenarios.py`): byte 0 = `~mask & 0xff`, byte 1 =
`~(mask >> 8) & 0xff`. The bit orders line up exactly. Pressure is `0xff` when held and `0` otherwise;
analog sticks are neutral at `0x7f`.

## 2. Playback (2026-11-01)

PCSX2 has **no command-line option** for input playback (`-help` lists none). It works from the GUI:
Tools → Input Recording → Play, then System → Pause to resume (the file dialog pauses emulation). Driven
remotely with `xdotool` on the KDE/X11 session (`DISPLAY=:0`, env taken from `plasmashell`); PCSX2
restarted with `-nofullscreen` so the menu bar is reachable.

Our generated `out/p2m2/p1_race_snow_jam.p2m2` (upstream's `p1_race_snow_jam` input script, 7950 frames)
**drove the game from a cold boot through the menus into a Snow Jam race** with nobody touching the
controller, and PINE kept working throughout. Race counter first seen ~100 s in; at the end of playback
(frame 7950, auto-paused) the race frame was **3498**.

**First real comparison.** The same script natively (`ssx3-headless 7950`) reached race frame **4398**:
the native race starts ~900 frames (~15 s) earlier (native file loads are instant; PCSX2 emulates disc
timing). Lined up by race frame 3498, every rider's position and velocity differ, because the gameplay
presses are timed from boot and so land on different race frames on each side.

**Consequence for the runner (Task 8):** split each script into menu presses (boot-relative) and in-race
presses (race-relative). Measure each side's race-start boot frame (one native run; one PCSX2 playback),
then shift the in-race presses per side so they hit the same race frames. Both sides are deterministic, so
the start frames are stable.

## 3. PINE and the frame counter (2026-11-01)

**PINE from outside the RetroDECK sandbox works.** The socket is sandbox-private
(`/run/user/1000/pcsx2.sock` inside), but reachable as
`PCSX2_PINE_SOCK=/proc/<pcsx2-qt pid>/root/run/user/1000/pcsx2.sock`.
`pine.py info` → `PCSX2 v2.8.2 | SSX 3 | SLUS-20772 1.00 | running`.

**Race frame counter:** `AI_GetFrameCounter` (0x1298c8) reads `App → +0x84 → +0xc → +8`, with
`App` at `gp - 0x848` = **`0x4a28a8`** (`GAME_GP` = 0x4a30f0). Native race (`SSX3_EVENT=BRA2`): 805, 815,
905 at headless frames 1000, 1010, 1100, so +1 per frame. The chain is null outside a race.

**No shared always-on counter yet.** Words that tick everywhere (`EA_TIMER_TICKS` 0x450dcc, 0x450dd0,
`App+0x18` (`APPMAN_VSYNC`) 0x4c9440, `App+0x1c` 0x4c9444, 0x44c468, 0x50aaa8) rise **+1 per vsync in
PCSX2** (60/s, sampled over 2 s at the menus) but **+10 per headless frame natively**. Either a headless
frame isn't one vsync for these, or the native vblank-driven timers run 10× fast. **Open question for
upstream**; don't use these to line frames up.

Without `SSX3_ISO` the headless runner can't find the disc and idles at boot (RAM never changes). Always
`. ./.envrc` first.

Checked in PCSX2 during a Snow Jam race (user-driven): the race counter rose +60 per second, i.e. +1 per
frame, and `fields.toml` resolved and sampled live in one PINE batch (frame 5070, 6 riders, 1 player).
Natively (`SSX3_EVENT=BRA2`, chains resolved from a RAM dump) the same fields trace correctly.

## Decision

- **Races: `MODE = per-frame`**, lined up by the race frame counter (`frame` in `fields.toml`).
  Pointer-chain fields are resolved once per side at race start (PINE live; native from a RAM dump at a
  frame inside the race), then sampled as plain addresses.
- **Menus: `MODE = end-of-run`** until a shared always-on counter is found (see the 10× question above).
- `.p2m2` playback (step 2) still needs one manual load in PCSX2 (Tools → Input Recording → Play).
