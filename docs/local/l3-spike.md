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

## 2. Playback from the command line

Pending (needs PCSX2 running with the disc).

## 3. PINE during playback, and the frame counter

Pending (needs PCSX2 running, and Ghidra for the frame-counter address).

## Decision

Pending.
