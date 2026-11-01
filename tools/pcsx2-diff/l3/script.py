"""Scenario input scripts (SSX3_INPUT `frame:buttons:frames,...`): split into menu presses (timed from
boot) and in-race presses, and re-time the in-race part per side so it lands on the same race frames.

The native build reaches a race ~900 frames before PCSX2 on the same script (docs/local/pcsx2-comparison.md),
so boot-timed riding inputs hit different race frames on each side.
"""
from dataclasses import dataclass

CIRCLE = 0x2000
RIDE_HOLD = 60  # scenarios.gameplay() opens with a 60-frame Circle hold (boost while steering)


@dataclass(frozen=True)
class Press:
    start: int
    mask: int
    n: int


def parse_script(s):
    out = []
    for item in filter(None, s.split(",")):
        f, b, n = item.split(":")
        out.append(Press(int(f), int(b, 16), int(n)))
    return out


def format_script(presses):
    return ",".join(f"{p.start}:{p.mask:04x}:{p.n}" for p in presses)


def gameplay_start(presses):
    """Boot frame of the first riding press (scenarios.gameplay()), or None if the script never rides."""
    for p in presses:
        if p.mask & CIRCLE and p.n == RIDE_HOLD:
            return p.start
    return None


def split(presses, gameplay_frame):
    return ([p for p in presses if p.start < gameplay_frame],
            [p for p in presses if p.start >= gameplay_frame])


def shift(presses, offset):
    return [Press(p.start + offset, p.mask, p.n) for p in presses if p.start + offset >= 0]


def trim_menu(menu, race_start, margin):
    """Drop menu presses starting at or after `race_start - margin`: the "X until the event has surely
    started" spam would otherwise act in the race, at different race frames per side. The press that
    starts the race (the counter starts 2 frames after an X on both sides) is kept, so trimming does
    not move the race start."""
    return [p for p in menu if p.start < race_start - margin]


def per_side_script(presses, race_start, ref_race_start, margin=0):
    """The script for one side: menu presses unchanged (trimmed before this side's race start), riding
    presses moved by (race_start - ref_race_start) so they hit the same race frames as the reference."""
    g = gameplay_start(presses)
    if g is None:
        return format_script(presses)
    menu, race = split(presses, g)
    return format_script(trim_menu(menu, race_start, margin) + shift(race, race_start - ref_race_start))
